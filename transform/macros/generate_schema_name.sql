{#
  dbt's default is to *concatenate*: target schema + "_" + custom schema, so
  `+schema: staging` would land in `marts_staging`. Sensible for shared
  warehouses where every developer needs their own namespace; noise for a lab
  with one reader. This standard override uses the custom name verbatim.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
