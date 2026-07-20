from pydantic import BaseModel, Field
from typing import Optional, Union

class Address(BaseModel):
    building: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[str] = None
    county: Optional[str] = None
    country: Optional[str] = None

class Amount(BaseModel):
    requested: float
    currency: str

class Merchant(BaseModel):
    iban: Optional[str] = None
    accountIdentifier: Optional[str] = None
    bankCode: Optional[str] = None
    mcc: Optional[str] = None
    merchantName: Optional[str] = None
    merchantId: Optional[str] = None
    spCode: Optional[str] = Field(default=None, alias="sp")
    storeId: Optional[str] = None
    cashDeskId: Optional[str] = None
    label: Optional[str] = None
    vat: Optional[str] = None
    address: Optional[Address] = None

    class Config:
        populate_by_name = True

class Buyer(BaseModel):
    iban: Optional[str] = None
    accountIdentifier: Optional[str] = None
    bankCode: Optional[str] = None
    mobile: Optional[str] = None
    name: Optional[str] = None

class VerifyReserveRequest(BaseModel):
    transactionId: str
    amount: Amount
    reason: Optional[str] = None
    merchant: Merchant
    buyer: Buyer
    requestToPay: Optional[bool] = False
    merchantTrxId: str
    transactionType: str

class MerchantVerifyReserveRequest(BaseModel):
    transactionId: str
    refTransactionId: Optional[str] = None
    amount: Amount
    reason: Optional[str] = None
    merchant: Merchant
    buyer: Buyer
    requestToPay: Optional[bool] = False
    transactionType: str
    merchantTrxId: str
    refMerchantTrxId: Optional[str] = None
    categoryPurpose: str

class VerifyReserveResponse(BaseModel):
    outcome: str
    errorMsg: str
    transactionType: str
    merchantTrxId: str
    authorisationId: Optional[str] = None
    authorizationID: Optional[str] = None

class SCTInitiationRequest(BaseModel):
    transactionId: str
    refTransactionId: Optional[str] = None
    refAuthorizationId: Optional[str] = None
    amount: Amount
    reason: Optional[str] = None
    merchant: Merchant
    buyer: Buyer
    requestToPay: Optional[bool] = False
    transactionType: str
    merchantTrxId: Optional[str] = None
    refMerchantTrxId: Optional[str] = None
    categoryPurpose: str

class SCTInitiationResponse(BaseModel):
    outcome: str
    errorMsg: str
    transactionType: str
    merchantTrxId: str
    authorizationID: Optional[str] = None
    TRN: Optional[str] = None

class VerifyDebtorPayment(BaseModel):
    amount: float
    currency: str
    transactionType: str
    transactionId: str
    refTransactionId: Optional[str] = None
    refMerchantTrxId: Optional[str] = None
    merchantTrxId: Optional[str] = None
    requestToPay: Optional[bool] = False
    reservefunds: Optional[bool] = True
    refAuthorizationId: Optional[str] = None
    reason: Optional[str] = None
    executionDateTime: Optional[str] = None

class CreditorAccount(BaseModel):
    iban: Optional[str] = None
    accountIdentifier: Optional[str] = None
    creditorName: Optional[str] = None

class VerifyDebtorCreditor(BaseModel):
    creditorAccount: CreditorAccount
    groupCode: Optional[str] = None
    bankCode: Optional[str] = None
    mobile: Optional[str] = None
    mcc: Optional[str] = None
    label: Optional[str] = None
    merchantId: Optional[str] = None
    storeId: Optional[str] = None
    cashDeskId: Optional[Union[int, str]] = None
    vat: Optional[str] = None
    address: Optional[Address] = None

class DebtorAccount(BaseModel):
    iban: Optional[str] = None
    accountIdentifier: Optional[str] = None
    debtorName: Optional[str] = None

class VerifyDebtorDebtor(BaseModel):
    debtorAccount: DebtorAccount
    groupCode: Optional[str] = None
    bankCode: Optional[str] = None
    mobile: Optional[str] = None
    mcc: Optional[str] = None
    label: Optional[str] = None
    merchantId: Optional[str] = None
    storeId: Optional[str] = None
    cashDeskId: Optional[Union[int, str]] = None
    vat: Optional[str] = None
    address: Optional[Address] = None

class VerifyDebtorAccountRequest(BaseModel):
    payment: VerifyDebtorPayment
    categoryPurpose: str
    creditor: VerifyDebtorCreditor
    debtor: VerifyDebtorDebtor

class DebtorAccountResp(BaseModel):
    iban: Optional[str] = None
    accountIdentifier: Optional[str] = None

class VerifyDebtorAccountResponse(BaseModel):
    outcome: str
    errorMsg: str
    transactionType: Optional[str] = None
    merchantTrxId: Optional[str] = None
    authorizationID: Optional[str] = None
    debtorAccount: Optional[DebtorAccountResp] = None

class SCTInitiationRequestV2(BaseModel):
    payment: VerifyDebtorPayment
    categoryPurpose: str
    creditor: VerifyDebtorCreditor
    debtor: VerifyDebtorDebtor



