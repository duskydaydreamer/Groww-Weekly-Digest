# Weekly Review Pulse
*Generated for the week of **{{ week_label }}***

---

## Top Themes

{% for theme in top_themes %}
### {{ loop.index }}. {{ theme.name }}
> **Overview:** {{ theme.summary }}
> *Avg Sentiment: {{ theme.avg_sentiment }} | Actionable Issues: {{ theme.actionable_count }}*

{% endfor %}

---

## User Voices

{% for quote in user_quotes %}
> *"{{ quote.text }}"*

{% endfor %}

---

## Recommended Actions

{% for action in action_ideas %}
- [ ] **{{ action }}**
{% endfor %}

---
*Data Source: Analyzed {{ total_reviews }} reviews from {{ sources | join(", ") }} for the period of {{ period_start }} to {{ period_end }}.*
