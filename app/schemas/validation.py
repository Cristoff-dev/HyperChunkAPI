from pydantic import BaseModel, EmailStr, Field, field_validator

class ProductRowSchema(BaseModel):
    sku: str = Field(..., min_length=5, description="Stock Keeping Unit único")
    product_name: str = Field(..., min_length=2)
    price: float = Field(..., gt=0, description="El precio debe ser mayor a 0")
    stock: int = Field(..., ge=0, description="El stock no puede ser negativo")
    supplier_email: EmailStr

    @field_validator('sku')
    @classmethod
    def sku_must_be_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('El SKU debe ser alfanumérico')
        return v.upper()