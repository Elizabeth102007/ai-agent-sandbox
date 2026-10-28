from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, Literal

class LineItem(BaseModel):
    description: Optional[str] = Field(default=None,description="Description of the line item.")
    quantity: Optional[float] = Field(default=None, description="Quantity of the line item.")
    unit_price: Optional[float] = Field(default=None, description="Unit price of the line item.")
    amount: Optional[float] = Field(default=None, description="Total amount for the line item.")
    
class ExtractedInvoice(BaseModel):
    vendor: Optional[str] = Field(default=None, description="The name of the vendor.")
    invoice_number: Optional[str] = Field(default=None, description="The invoice number.")
    invoice_date: Optional[str] = Field(default=None, description="The date the invoice was issued.")
    due_date: Optional[str] = Field(default=None, 
                                    description="The due date of the invoice.")
    currency: Optional[str] = Field(
            default=None,
            description="Three-letter currency code, or null if unknown."
        )
    line_items: list[LineItem] = Field(default_factory=list, description="List of line items in the invoice.")
    subtotal: Optional[float] = Field(default=None, description="The subtotal amount of the invoice.")
    tax: Optional[float] = Field(default=None, description="The tax amount of the invoice.")
    total: Optional[float] = Field(default=None,description="The total amount of the invoice.")


class InvoiceResult(BaseModel):
    invoice: Optional[ExtractedInvoice] = Field(default=None, 
                                              description="The extracted invoice data.")
    errors: list[str] = Field(default_factory=list, 
                              description="List of errors encountered during extraction.")
    attempts: int = Field(default=0, 
                          description="Number of attempts made to extract the invoice.")
    status: Literal["validated", "needs_review"] = Field(description="The status of the extracted invoice.")

    @model_validator(mode="after")
    
    def enforce_status_and_errors(self):
        if self.status == "validated":
            if self.errors:
                raise ValueError("A validated result must contain no errors ")

            if self.invoice is None:
                raise ValueError("A validated result must contain an invoice")

        elif self.status == "needs_review":
            if not self.errors:
                raise ValueError("Status 'needs_review' requires at least one error message.")
        return self

        