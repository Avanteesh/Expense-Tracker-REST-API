from sqlmodel import SQLModel,String,create_engine,Field
from sqlmodel import Relationship,Date
from uuid import uuid4
from typing import Optional, List
from datetime import datetime

DBengine = create_engine("sqlite:///expense.db")

# database schema!    
class User(SQLModel,table=True):
    id: str = Field(default=str(uuid4()),primary_key=True)
    username: str = Field(String,unique=True)
    email: str = Field(String,unique=True)
    password: str = Field(String)
    bankaccount: List["BankAccount"] = Relationship(back_populates='user')
    
class BankAccount(SQLModel,table=True):
    account_id: str = Field(default=str(uuid4()),primary_key=True)
    account_name: str = Field(String, unique=True)
    bank_balance: float = Field(default=0)
    expense: List['Expense'] = Relationship(back_populates='account')
    user_id: Optional[str] = Field(String,foreign_key="user.id")  # foreign key referencing User.id
    user: List[User] = Relationship(back_populates="bankaccount")
    
class Expense(SQLModel,table=True):
    expense_id: str = Field(default=str(uuid4()), primary_key=True)
    ammount: float
    account_id: Optional[str] = Field(String,foreign_key='bankaccount.account_id') # foreign key ref BankAccount.id
    note: str = Field(String)
    payment_date: datetime = Field(default=datetime.now())  # default date as now for payment transaction or purchase
    account: Optional[BankAccount] = Relationship(back_populates='expense')

# store meta data as objects while fetching request in between
class AccountMetaData(SQLModel):
    account_name: str
    balance: float

class UserMetaData(SQLModel):
    user_id: str
    email: str
    password: str

class ExpenseMetaData(SQLModel):
    ammount: float
    account_name: str
    notes: str

class AccessToken(SQLModel):
    access_token: str
    token_type: str

SQLModel.metadata.create_all(DBengine)   # create ORM execution engine!
