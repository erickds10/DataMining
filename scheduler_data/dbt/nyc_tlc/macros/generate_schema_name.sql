{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        -- Usa EXACTAMENTE el schema del modelo/carpeta (sin concatenar)
        {{ custom_schema_name | upper }}
    {%- endif -%}
{%- endmacro %}
