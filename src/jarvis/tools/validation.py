"""JSON Schema local sin referencias remotas ni resolución de recursos externos."""
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

# Subconjunto deliberado y portable para definiciones de herramientas.
KEYWORDS = {"type", "description", "properties", "required", "additionalProperties",
            "items", "minItems", "maxItems", "uniqueItems", "enum", "const",
            "minimum", "maximum", "minLength", "maxLength", "pattern"}


def validate_schema(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ValueError("Esquema de herramienta inválido.") from error

    def visit(rule):
        if not isinstance(rule, dict) or set(rule) - KEYWORDS:
            raise ValueError("El esquema utiliza palabras clave no admitidas.")
        if "type" not in rule:
            raise ValueError("Cada regla necesita un tipo explícito.")
        if rule["type"] == "object":
            properties = rule.get("properties", {})
            if set(rule.get("required", [])) - set(properties):
                raise ValueError("Un parámetro obligatorio no está declarado.")
            for child in properties.values():
                visit(child)
            if isinstance(rule.get("additionalProperties"), dict):
                visit(rule["additionalProperties"])
        if rule["type"] == "array":
            if "items" not in rule:
                raise ValueError("Las listas necesitan un esquema items.")
            visit(rule["items"])
    visit(schema)


def validate_arguments(arguments, schema):
    error = next(Draft202012Validator(schema).iter_errors(arguments), None)
    if error:
        # No incluir valores del usuario ni el mensaje completo del validador.
        raise ValueError(f"Argumentos incompatibles con el esquema ({error.validator}).")
    for name, value in arguments.items():
        if isinstance(value, str) and schema.get("properties", {}).get(name, {}).get("minLength", 0) > 0 and not value.strip():
            raise ValueError("Los parámetros de texto no pueden contener solo espacios.")
