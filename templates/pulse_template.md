# 📊 Weekly Review Pulse
## {{ week_label }}

### 📌 Top Themes
{% for theme in top_themes %}
{{ loop.index }}. **{{ theme.name }}** — {{ theme.summary }} _(Avg Sentiment: {{ theme.avg_sentiment }} | Actionable Issues: {{ theme.actionable_count }})_
{% endfor %}

### 💬 User Voices
{% for quote in user_quotes %}
- "{{ quote.text }}"
{% endfor %}

### 🎯 Action Ideas
{% for action in action_ideas %}
{{ loop.index }}. {{ action }}
{% endfor %}

---
_Reviews analyzed: {{ total_reviews }} | Sources: {{ sources | join(", ") }} | Period: {{ period_start }} – {{ period_end }}_
