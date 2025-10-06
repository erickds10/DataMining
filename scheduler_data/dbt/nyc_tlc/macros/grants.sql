{% macro apply_standard_grants(target_relation) %}
  {% set grant_role = env_var('SNOWFLAKE_ROLE') %}
  {% if grant_role %}
    grant usage on schema {{ target_relation.database }}.{{ target_relation.schema }} to role {{ grant_role }};
    grant select on {{ target_relation }} to role {{ grant_role }};
  {% endif %}
{% endmacro %}
