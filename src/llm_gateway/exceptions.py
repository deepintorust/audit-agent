class LLMGatewayError(Exception):
    pass


class RetryExhaustedError(LLMGatewayError):
    pass


class TransportError(LLMGatewayError):
    pass


class PayloadBuildError(LLMGatewayError):
    pass


class UnsupportedProviderError(LLMGatewayError):
    pass
