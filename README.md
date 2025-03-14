
# Expense Tracker REST-API with OAuth2-authentication

<p>
an expense tracker api that helps you save your daily expenses by tracking it based on different accounts
also, provides a little data analytics get insight of the rate at which your spending and when you might run out of balance. This is probably one of the coolest projects I have made!
</p>

<details>
<summary>Project External Dependencies</summary>
<ul>
<li>Python framework FastAPI (version 0.0.6 CLI)</li>
<li>SQLmodel (SQL ORM) using sqlite3</li>
<li>passlib (Crypto library)</li>
<li>python-jose for JSON Web token handling!</li>
<li>numpy and random for a little data analytics!</li>
</ul>
</details>


<span>Before running, Make sure to initialize '.env' file with the variables
<ul>
  <li>SECRET_KEY (key larger than 64 bit is encouraged!)</li>
  <li>ALGORITHM (the hasing algorithm, You can use HS256)</li>
  <li>TOKEN_EXPIRE_TIME (expiry time of JWT token, a Number string!)</li>
</ul>
</span>
<h5>Run the server with Docker-cli</h5>
