import os
import json

import streamlit as st
from openai import OpenAI

# -----------------------------
# Basic config
# -----------------------------
st.set_page_config(
    page_title="EquiAid Navigator",
    page_icon="🌍",
    layout="wide",
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

if not OPENAI_API_KEY:
    st.warning(
        "⚠️ OPENAI_API_KEY is not set in your environment. "
        "Set it before running this app to enable AI-powered recommendations."
    )

# -----------------------------
# AI helper
# -----------------------------
def ai_fetch_awards(profile: dict):
    """
    Uses OpenAI to return a JSON list of awards/benefits relevant to the profile.

    NOTE:
    - This does NOT guarantee legal eligibility.
    - Results may not be fully up to date.
    - User must verify on the official sites.
    """
    if client is None:
        raise RuntimeError("OpenAI client not initialized. Set OPENAI_API_KEY.")

    system_message = (
        "You are an assistant that helps underserved people in the United States "
        "discover scholarships, education awards, housing support, and food/nutrition "
        "assistance programs. You respond ONLY with strict JSON. "
        "For each item, include: name, category, description, link, why_it_matches. "
        "Categories must be one of: "
        "['scholarship','grant','housing_support','food_nutrition','workforce_program','other']. "
        "Prioritize: Indigenous/Native heritage, low-income households, first-generation "
        "students, rural families, recent immigrants, and single-parent households when relevant. "
        "All programs must be legal, legitimate, and US-based. "
        "Prefer official .gov, .edu, or recognized nonprofit URLs when possible. "
        "If you are not sure, include the best known official or widely-recognized site. "
        "Do NOT invent fake organizations or fake government programs."
    )

    user_profile_str = json.dumps(profile, ensure_ascii=False, indent=2)

    user_message = f"""
Given this user profile:

{user_profile_str}

Return a JSON object with the following structure:

{{
  "awards": [
    {{
      "name": "string",
      "category": "one of ['scholarship','grant','housing_support','food_nutrition','workforce_program','other']",
      "description": "short, clear description (max 60 words)",
      "link": "direct URL to learn/apply",
      "why_it_matches": "1–2 sentences tying the program to the user's background"
    }}
  ]
}}

Include 8–15 high-quality items. Focus on relevance over quantity.
If the user is in a particular state, try to include that state's programs when possible.
If a well-known national program applies, include it too.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    awards = data.get("awards", [])
    return awards


# -----------------------------
# Main UI
# -----------------------------
def main():
    st.title("🌍 EquiAid Navigator")
    st.write(
        "Use this tool to discover **scholarships, grants, housing, and food support programs** "
        "you might be able to apply for. We’ll use your answers *only in this session* to ask AI "
        "for relevant programs and links — we don’t create an account or store your information."
    )

    st.markdown(
        "⚠️ **Important:** This is an AI-assisted navigator, not legal or financial advice. "
        "Always double-check details, eligibility, and deadlines on the official websites "
        "before applying."
    )

    st.markdown("---")

    # -------------------------
    # Profile input (no storage)
    # -------------------------
    st.subheader("1️⃣ Tell us a bit about your situation")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            background_categories = st.multiselect(
                "Which of these describe your situation? (choose all that apply, optional)",
                options=[
                    "Indigenous or Native heritage",
                    "Low-income household",
                    "First-generation college student",
                    "Rural household",
                    "Recent immigrant",
                    "Single-parent household",
                    "Military family",
                    "Caregiver for children or relatives",
                ],
                help="This helps AI recommend programs that are designed for specific groups.",
            )

            income_range = st.selectbox(
                "Approximate household income range (USD)",
                options=[
                    "Prefer not to say",
                    "0–20,000",
                    "20,001–40,000",
                    "40,001–60,000",
                    "60,001–80,000",
                    "80,001–100,000",
                    "100,001+",
                ],
            )

            household_size = st.number_input(
                "Number of people in your household",
                min_value=1,
                max_value=20,
                value=1,
            )

        with col2:
            state = st.text_input(
                "State (e.g., TX, OH)",
                help="Two-letter abbreviation if possible, like TX, CA, NY.",
            )
            zip_code = st.text_input(
                "ZIP code (optional)",
                help="Including this can help AI surface more local programs.",
            )
            education_goal = st.selectbox(
                "Main education or career goal",
                options=[
                    "High school completion",
                    "Associate degree",
                    "Bachelor's degree",
                    "Graduate studies",
                    "Vocational / technical training",
                    "Job training / workforce program",
                    "Other / not sure yet",
                ],
            )

        submitted = st.form_submit_button("🔎 Find awards and benefits")

    # -------------------------
    # Handle submission
    # -------------------------
    if submitted:
        if not OPENAI_API_KEY:
            st.error(
                "OPENAI_API_KEY is not set. Please set it in your environment "
                "before running the app."
            )
            return

        profile = {
            "background_categories": background_categories,
            "income_range": income_range,
            "household_size": int(household_size),
            "state": state.strip().upper(),
            "zip_code": zip_code.strip(),
            "education_goal": education_goal,
        }

        with st.spinner("Asking AI to find relevant programs for you..."):
            try:
                awards = ai_fetch_awards(profile)
            except Exception as e:
                st.error(f"Error while contacting AI: {e}")
                return

        st.markdown("---")
        st.subheader("2️⃣ Recommended programs for you")

        if not awards:
            st.warning(
                "No programs were returned this time. You can try again later, "
                "or adjust your answers slightly (for example, add more background details "
                "or include your state)."
            )
            return

        for idx, award in enumerate(awards, start=1):
            with st.container():
                st.markdown(f"**{idx}. {award.get('name', '(no name)')}**")
                st.caption(f"Category: {award.get('category', 'N/A')}")
                st.write(award.get("description", ""))

                link = award.get("link")
                if link:
                    st.markdown(f"[Open official page]({link})")

                st.markdown(
                    f"*Why this was recommended:* {award.get('why_it_matches', 'No explanation provided.')}"
                )
                st.markdown("---")

        st.caption(
            "⚠️ This list is generated by AI based on publicly known programs. "
            "It may not include all opportunities and might not always be fully up to date. "
            "Always confirm eligibility and details on the official sites."
        )


if __name__ == "__main__":
    main()