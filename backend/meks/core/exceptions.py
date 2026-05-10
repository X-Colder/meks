from fastapi import HTTPException, status


class MeksException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class UnauthorizedException(MeksException):
    def __init__(self, detail: str = "认证失败"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(MeksException):
    def __init__(self, detail: str = "权限不足"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(MeksException):
    def __init__(self, resource: str = "资源"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource}不存在"
        )


class ConflictException(MeksException):
    def __init__(self, detail: str = "资源已存在"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
