Subject: 📊 Weekly Review Pulse — {{ week_label }}

Hello Team,

Here is the Weekly Review Pulse for {{ period_start }} to {{ period_end }}.

{% if doc_url %}
**[View the full report on Google Docs]({{ doc_url }})**
{% endif %}

### 📌 Top Themes
{% for theme in top_themes %}
{{ loop.index }}. **{{ theme.name }}**
{% endfor %}

### 🎯 Action Ideas
{% for action in action_ideas %}
- {{ action }}
{% endfor %}

Best,
AI Review Summarizer Engine
