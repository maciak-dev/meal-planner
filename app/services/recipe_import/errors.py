class RecipeImportError(Exception):
    """Bazowa klasa błędów importu - zawsze niesie czytelny komunikat dla użytkownika."""


class InvalidUrlError(RecipeImportError):
    pass


class BlockedHostError(RecipeImportError):
    pass


class TooManyRedirectsError(RecipeImportError):
    pass


class FetchTimeoutError(RecipeImportError):
    pass


class ResponseTooLargeError(RecipeImportError):
    pass


class UnsupportedContentTypeError(RecipeImportError):
    pass


class UpstreamFetchError(RecipeImportError):
    pass


class NoRecipeFoundError(RecipeImportError):
    pass
