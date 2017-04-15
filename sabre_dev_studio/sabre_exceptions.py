class SabreClientError(Exception):
    pass

# Authentication requested, but no credentials (client ID, client secret) provided
class NoCredentialsProvided(SabreClientError):
    pass

# Did not request token
class NotAuthorizedError(SabreClientError):
    pass

class UnsupportedMethodError(SabreClientError):
    pass

class InvalidInputError(SabreClientError):
    pass

# Base API Exception
class SabreDevStudioAPIException(Exception):
    def __init__(self, e=None):
        if isinstance(e, dict):
            message = e.get('message')
            super(SabreDevStudioAPIException, self).__init__(message)

            self.message = message
            self.status = e.get('status')
            self.error_code = e.get('errorCode')
            self.e_type = e.get('type')
            self.tstamp = e.get('timeStamp')
        elif isinstance(e, str):
            self.message = e
        else:
            super(SabreDevStudioAPIException, self).__init__()

    def __unicode__(self):
        if self.message and self.status:
            str += 'Message:\t' + self.message + '\n'
            str += 'Status:\t' + self.status + '\n'
            str += 'Error Code:\t' + self.error_code + '\n'
            str += 'Type:\t' + self.type + '\n'
            str += 'Timestamp:\t' + self.timestamp + '\n'
            return str
        elif self.message:
            return self.message
        else:
            return "<" + self.__class__.__name__ + ">"


# 400
class SabreErrorBadRequest(SabreDevStudioAPIException):
    pass

# 401
class SabreErrorUnauthorized(SabreDevStudioAPIException):
    pass

# 403
class SabreErrorForbidden(SabreDevStudioAPIException):
    pass

# 404
class SabreErrorNotFound(SabreDevStudioAPIException):
    pass

# 404
class SabreErrorMethodNotAllowed(SabreDevStudioAPIException):
    pass

# 406
class SabreErrorNotAcceptable(SabreDevStudioAPIException):
    pass

# 429
class SabreErrorRateLimited(SabreDevStudioAPIException):
    pass

# 500
class SabreInternalServerError(SabreDevStudioAPIException):
    pass

# 503
class SabreErrorServiceUnavailable(SabreDevStudioAPIException):
    pass

# 504
class SabreErrorGatewayTimeout(SabreDevStudioAPIException): 
    pass

class SabreErrorUnauthenticated(SabreDevStudioAPIException):
    pass