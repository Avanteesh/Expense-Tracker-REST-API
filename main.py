from fastapi import FastAPI,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from sqlmodel import select, Session, update
from models import User,BankAccount,Expense,AccountMetaData
from models import AccessToken,DBengine,UserMetaData,ExpenseMetaData
from passlib.context import CryptContext
from dotenv import load_dotenv
from os import environ
from functools import reduce
from jose import JWTError, jwt
from numpy import array as np_array, median as np_median
from numpy.random import randint

load_dotenv()
app = FastAPI()
session = Session(DBengine)
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def fetchUserData(username: str):
    query = select(User).where(User.username == username)
    response = session.exec(query).first()
    if not response:
        return
    return UserMetaData(
      user_id=response.id,email=response.email,
      password=response.password
    )

def authenticate(username: str, password: str):
    fetched = fetchUserData(username)
    if not fetched:
        return False    # user does not exist
    elif not pwd_context.verify(password, fetched.password):
        return False
    return fetched

def createAccessToken(data: dict):
    copied = data.copy()
    tokenExpiry = datetime.utcnow() + timedelta(minutes=int(environ.get('TOKEN_EXPIRE_TIME')))
    copied.update({"exp": tokenExpiry})
    jwt_token =  jwt.encode(
      copied,environ.get('SECRET_KEY'),algorithm=environ.get('ALGORITHM')
    )
    return jwt_token

async def getCurrentUser(token: str=Depends(oauth2_scheme)):
    credential_exception = HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail='Could not fetch details',
      headers={"WWW-Authenticate":"Bearer"}
    )
    username = None
    try:
        datapayload = jwt.decode(
          token, environ.get('SECRET_KEY'),algorithms=[environ.get('ALGORITHM')]
        )
        username = datapayload.get('sup')
        if username is None:
            raise credential_exception
    except JWTError:
        raise credential_exception
    user_data = fetchUserData(username)
    if not user_data:
        raise credential_exception 
    return user_data

async def getActiveUser(current_user: UserMetaData=Depends(getCurrentUser)) -> User or None:
    user_info = select(User.id, User.username).where(
      User.id == current_user.user_id
    ).where(
      User.email == current_user.email
    ).where(
      User.password == current_user.password
    )
    response = session.exec(user_info).first()
    return response

@app.post("/sign-in")
async def signIn(user: User):
    query = select(User).where(
      User.id == user.id
    ).where(
      User.email == user.email    
    ).where(User.username == user.username)
    result = session.exec(query).fetchall()
    if len(result) != 0:
        return {"message": "Oops something went wrong! Try again!"}
    else:
        session.add(User(
         id=user.id, email=user.email,
         username=user.username,password=pwd_context.hash(user.password)
        ))
        session.commit()
        return {"message":"Your signed in!"}

@app.post("/token", response_model=AccessToken)
async def login(formData: OAuth2PasswordRequestForm=Depends()):
    user = authenticate(formData.username,formData.password)
    if not user:
        raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Unauthorized User!",
          headers={"WWW-Authenticate":"Bearer"}
        ) 
    accessToken = createAccessToken({'sup':formData.username})
    return AccessToken(**{"access_token":accessToken,"token_type":"bearer"})

@app.get("/profile")
async def autoSign(current_user: User=Depends(getActiveUser)):
    return {"message": f"hello there {current_user.username}"}


@app.get("/showmy-bankaccounts")
async def showBankAccounts(active_user: User=Depends(getActiveUser)):
    bank_account_query = select(
      User.username,BankAccount.account_id, 
      BankAccount.account_name,BankAccount.bank_balance
    ).where(User.id == BankAccount.user_id)
    result = session.exec(bank_account_query).fetchall()
    jsonified = [
      {"account_id":item[1],"account_name":item[2],"balance":item[3]} 
      for item in result
    ]
    response = {
      "message": ("You have got no accounts yet" if len(result) == 0 else "Your accounts"),
      "data": jsonified
    }
    return response

@app.post("/new-bankaccount")
async def createNewAccount(account: AccountMetaData, active_user: User=Depends(getActiveUser)):
    if account.balance < 0:
        return {"message": "Invalid input! balance must be a positive amount"}
    else:
        search_query = session.exec(select(BankAccount).where(
          BankAccount.account_name == account.account_name
        )).fetchall()
        if len(search_query) != 0:
            return {"message": "Looks Like this account already exists!"}
        else:
            session.add(BankAccount(
              account_name=account.account_name,bank_balance=account.balance,
              user_id=active_user.id
            ))
            session.commit()
            return {"message": "Acccount Created Successfully!"}


@app.post("/new-expense")
async def addNewExpense(expense: ExpenseMetaData, active_user: User=Depends(getActiveUser)):
    if expense.ammount <= 0:
        return {"message": "Thats not a valid amount!"}
    search = session.exec(select(BankAccount).where(
      BankAccount.account_name == expense.account_name
    )).first()
    if search is None:
        return {"message": f"This Account: {expense.account_name} Doesn't exist!"}
    elif expense.ammount > search.bank_balance:
        return {"message": "Looks like you don't have enough Balance!"}
    else:
        session.exec(
          update(BankAccount).where(
            BankAccount.account_name == expense.account_name
          ).values(bank_balance=BankAccount.bank_balance - expense.ammount)
        )
        new_expense = Expense(ammount=expense.ammount,account_id=search.account_id,note=expense.notes)
        session.add(new_expense)
        session.commit()
        return {"message": "Success!"}


@app.get("/expenses-history/")
async def expenseHistory(account: str=None, active_user: User=Depends(getActiveUser)):
    if account is not None:
        expenses_from = session.exec(
          select(Expense.ammount,Expense.note,Expense.payment_date,BankAccount.account_name).join(
            Expense,Expense.account_id == BankAccount.account_id
          ).where(
            BankAccount.account_name == account
          ).where( 
            BankAccount.user_id == active_user.id  
          )
        ).fetchall()
        jsonified = [{"payment_date": item[2],"ammount":item[0],"note":item[1]} for item in expenses_from] 
        return {"message": f"{account} payment history!", "data":jsonified}
    userexpenses = session.exec(
      select(Expense.ammount,Expense.note,Expense.payment_date,BankAccount.account_name).join(
       Expense, Expense.account_id == BankAccount.account_id
      ).where(BankAccount.user_id == active_user.id)
    ).fetchall()
    # sql query  
    """
    select amount,payment_date,account_name from Expense
    JOIN bankaccount on expense.account_id == bankaccount.account_id
    where bankaccount.user_id == active_user.id
    """
    jsonified = [{
      "payment_date": item[2],"ammount":item[0],"account_name":item[3],"notes":item[1]
    } for item in userexpenses]
    return {"message": "Your payment history", "data": jsonified}

@app.put("/update-balance")
async def updateBalanceForAccount(account_name: str,ammount: float,active_user: User=Depends(getActiveUser)):
    if ammount <= 0:
        return {"message": "The Ammount you entered is Invalid. Please try again!"}
    user_bankaccount = session.exec(
      select(BankAccount).where(
        BankAccount.user_id == active_user.id
      ).where(
        BankAccount.account_name == account_name
      )
    ).first()
    if user_bankaccount is None:
        return {"message": "The input account doesn't exist!"}
    session.exec(
      update(BankAccount).where(
        BankAccount.account_name == account_name
      ).where(
        BankAccount.user_id == active_user.id
      ).values(bank_balance = BankAccount.bank_balance + ammount)
    )
    session.commit()
    return {"message": "Balance updated succesfully!"}

@app.get("/expense-history-date")
async def getExpenseHistoryByDate(start: datetime, end: datetime, active_user: User=Depends(getActiveUser)):
    if start > end:
        return {
          "status": "failed",
          "message": "Please provide valid inputs!"
        }
    expenses = session.exec(
      select(Expense.ammount,Expense.note,Expense.payment_date,BankAccount.account_name).join(
        Expense, Expense.account_id == BankAccount.account_id
      ).where(
        BankAccount.user_id == active_user.id
      ).where(
        Expense.payment_date > start
      ).where(Expense.payment_date < end)
    ).fetchall()
    if len(expenses) == 0:
        return {"message": "No Records!"}
    jsonified = [{
      "ammount": item[0],"notes":item[1],"payment_date":item[2],"account_name":item[3]
    } for item in expenses]
    return {
      "status":"success",
      "message": f"{len(expenses)} records","data": jsonified
    }

@app.get("/total-expense")
async def getTotalExpense(days: int, accountName: str=None, active_user: User=Depends(getActiveUser)):
    if days < 0:
        return {
          "status": "failed",
          "message": "Please provide valid input!"
        }
    mindate: datetime = datetime.now() - timedelta(days)   # go 'days (argument)' days back!
    expenses, query = None, select(Expense.ammount,BankAccount.account_name).join(
      Expense,Expense.account_id == BankAccount.account_id
    ).where(BankAccount.user_id == active_user.id).where(
      Expense.payment_date >= mindate
    )
    if accountName is None:
        expenses = session.exec(query).fetchall()
    else:
        expenses = session.exec(query.where(
          BankAccount.account_name==accountName
        )).fetchall()
    if len(expenses) == 0:
        return {"message": "Oops the account name your provided doesn't exist!"}
    total: int = expenses[0][0] if len(expenses) == 1 else reduce(lambda a, b: a[0] + b[0], expenses)
    return {
      "status":"success", 
      "message": f"Your Total expense since last {days} days!", 
      "ammount": total
    }

# predict when user might run out of balance based on past expenses!
def predictExpenseRate(ammountSpent: list[int], bank_balance: float) -> datetime:
    median_expense = np_median(np_array(ammountSpent))  # median expense per-day!
    count = 0
    avg_range = (max(ammountSpent) + min(ammountSpent))/2
    while bank_balance > 0:
        bank_balance -= median_expense + randint(-avg_range, avg_range-1)  
        # adding random sampling, as expenses may not be the same everyday!
        count += 1  # increment day assuming
    return datetime.now() + timedelta(days=count)  

# reduce a list based on date
def reduceDataByDate(data):
    isSameDate = lambda a, b: a.year == b.year and a.month == b.month and a.day == b.day 
    newlist = []
    for k in range(len(data)):
        _sum, u = data[k][0], k+1
        while u < len(data):
            if isSameDate(data[k][2], data[u][2]) == False:
                break
            _sum += data[u][0]
            u += 1
        newlist.append(_sum)
    return newlist

@app.get("/tell-expense-rate")
async def expenseRate(accountName: str, active_user: User=Depends(getActiveUser)):
    accountExist = session.exec(
      select(BankAccount).where(BankAccount.account_name == accountName).where(
        BankAccount.user_id == active_user.id
      )
    ).fetchall()    
    # if account doesn't exist!
    if len(accountExist) == 0:
        return {
          "status": "failed",
          "message": f"looks like {accountName} account doesn't exist!"
        }
    query = session.exec(
      select(Expense.ammount,BankAccount.account_name,Expense.payment_date).join(
        Expense, Expense.account_id == BankAccount.account_id
      ).where(BankAccount.user_id == active_user.id).where(
        BankAccount.account_name == accountName
      )
    ).fetchall()
    getBalance = session.exec(
      select(BankAccount).where(BankAccount.account_name == accountName).where(
        BankAccount.user_id == active_user.id
      )
    ).first()
    if len(query) <= 1:
        return {
          "status":"success",
          "message": "Not enough data"
        }
    expense_perday = reduceDataByDate(query)
    estimate = predictExpenseRate(expense_perday, getBalance.bank_balance)
    return {
      "status": "success", 
      "message": "You might run out of balance by The following date",
      "date": estimate
    }
        
