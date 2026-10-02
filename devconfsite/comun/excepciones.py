from rest_framework.exceptions import APIException


class ReglaDeNegocio(APIException):
    status_code = 400
    default_detail = "This action is not allowed."
    default_code = "business_rule"
