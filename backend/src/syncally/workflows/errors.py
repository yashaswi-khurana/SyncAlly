"""Shared activity error-type names that define the workflow retry contract.

These string values are part of the durable Temporal retry contract. Changing
them alters how in-flight workflows treat activity failures.
"""

BUSINESS_REJECTION_ERROR_TYPE = "BusinessRejectionError"
VALIDATION_ERROR_TYPE = "ValidationError"
AUTHORIZATION_ERROR_TYPE = "AuthorizationError"
SECURITY_ERROR_TYPE = "SecurityError"

NON_RETRYABLE_ACTIVITY_ERROR_TYPES = (
    VALIDATION_ERROR_TYPE,
    BUSINESS_REJECTION_ERROR_TYPE,
    AUTHORIZATION_ERROR_TYPE,
    SECURITY_ERROR_TYPE,
)
