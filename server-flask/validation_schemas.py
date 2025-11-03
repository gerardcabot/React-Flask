"""
Validation schemas for API endpoints using Marshmallow.
Provides input validation and sanitization for all user-submitted data.
"""

from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class CustomModelTrainingSchema(Schema):
    """Schema for validating custom model training requests."""
    
    position_group = fields.Str(
        required=True,
        validate=validate.OneOf(
            ['Attacker', 'Midfielder', 'Defender'],
            error="Position group must be one of: Attacker, Midfielder, Defender"
        )
    )
    
    impact_kpis = fields.List(
        fields.Str(),
        required=True,
        validate=validate.Length(
            min=1,
            max=20,
            error="Impact KPIs must contain between 1 and 20 items"
        )
    )
    
    target_kpis = fields.List(
        fields.Str(),
        required=True,
        validate=validate.Length(
            min=1,
            max=30,
            error="Target KPIs must contain between 1 and 30 items"
        )
    )
    
    model_name = fields.Str(
        required=False,
        validate=validate.Length(
            max=100,
            error="Model name must be less than 100 characters"
        )
    )
    
    ml_features = fields.List(
        fields.Str(),
        required=False,
        allow_none=True,  
        validate=validate.Length(
            max=200,
            error="ML features list cannot exceed 200 items"
        )
    )


class PredictionRequestSchema(Schema):
    """Schema for validating prediction requests."""
    
    player_id = fields.Str(
        required=True,
        validate=validate.Length(
            min=1,
            max=50,
            error="Player ID must be between 1 and 50 characters"
        )
    )
    
    season = fields.Str(
        required=True,
        validate=validate.Regexp(
            r'^\d{4}_\d{4}$',
            error="Season must be in format YYYY_YYYY (e.g., 2015_2016)"
        )
    )
    
    model_id = fields.Str(
        required=False,
        validate=validate.Length(
            max=100,
            error="Model ID must be less than 100 characters"
        )
    )


class PlayerQuerySchema(Schema):
    """Schema for validating player data queries."""
    
    player_id = fields.Str(
        required=True,
        validate=validate.Length(
            min=1,
            max=50,
            error="Player ID must be between 1 and 50 characters"
        )
    )
    
    season = fields.Str(
        required=False,
        validate=validate.Regexp(
            r'^(\d{4}_\d{4}|all)$',
            error="Season must be in format YYYY_YYYY or 'all'"
        )
    )


class MetricQuerySchema(Schema):
    """Schema for validating metric query requests."""
    
    player_id = fields.Str(
        required=True,
        validate=validate.Length(
            min=1,
            max=50,
            error="Player ID must be between 1 and 50 characters"
        )
    )
    
    metric = fields.Str(
        required=True,
        validate=validate.Length(
            min=1,
            max=200,
            error="Metric name must be between 1 and 200 characters"
        )
    )
    
    season = fields.Str(
        required=False,
        validate=validate.Regexp(
            r'^\d{4}_\d{4}$',
            error="Season must be in format YYYY_YYYY"
        )
    )


def validate_request_data(schema_class, data, partial=False):
    """
    Validate request data against a schema.
    
    Args:
        schema_class: The Marshmallow schema class to use for validation
        data: The data to validate (usually request.get_json() or request.args)
        partial: Allow partial validation (for PATCH requests)
    
    Returns:
        tuple: (validated_data, error_response)
               If validation succeeds: (validated_data, None)
               If validation fails: (None, flask_jsonify_error_response)
    """
    from flask import jsonify
    
    schema = schema_class()
    try:
        validated_data = schema.load(data, partial=partial)
        return validated_data, None
    except ValidationError as err:
        error_response = jsonify({
            "error": "Validation error",
            "details": err.messages
        }), 400
        return None, error_response
