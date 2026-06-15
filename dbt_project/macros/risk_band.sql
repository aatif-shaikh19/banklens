{% macro risk_band(z_score_col) %}
CASE
    WHEN {{ z_score_col }} > 3  THEN 'Critical'
    WHEN {{ z_score_col }} > 2  THEN 'High'
    WHEN {{ z_score_col }} > 1  THEN 'Medium'
    ELSE 'Low'
END
{% endmacro %}
