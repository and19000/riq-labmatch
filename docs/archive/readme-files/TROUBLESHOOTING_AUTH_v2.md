# Troubleshooting Authentication Issues

If you can't log in after setting up access control, follow these steps:

## Step 1: Check Your Email in the Database

The email in `ALLOWED_USERS` must **exactly match** (case-insensitive) the email stored in your database when you signed up.

**Common issues:**
- Email in database: `YourEmail@Example.com`
- Email in ALLOWED_USERS: `youremail@example.com` ✅ (this works - case insensitive)
- Email in ALLOWED_USERS: `YourEmail@Example.com` ✅ (this also works)
- Email in ALLOWED_USERS: `your-email@example.com` ❌ (different email)

## Step 2: Verify ALLOWED_USERS Format

In your Render dashboard, check the `ALLOWED_USERS` environment variable:

**Correct format:**
```
your-email@example.com,collaborator@example.com
```

**Common mistakes:**
- ❌ `your-email@example.com, collaborator@example.com` (spaces after comma)
- ❌ ` your-email@example.com,collaborator@example.com ` (leading/trailing spaces)
- ❌ `"your-email@example.com,collaborator@example.com"` (quotes - don't include quotes)

## Step 3: Use the Debug Route (Development Only)

If you're running locally, visit:
```
http://localhost:5001/debug-auth
```

This will show you:
- What emails are in the ALLOWED_USERS list
- Your current logged-in email
- Whether you're authorized

## Step 4: Check Render Logs

1. Go to your Render dashboard
2. Click on your web service
3. Go to the **Logs** tab
4. Look for any error messages related to authentication

## Step 5: Verify Your Account Email

If you're not sure what email you used to sign up:

1. Try to reset your password using the "Forgot Password" link
2. If the email exists, you'll receive a reset link
3. This confirms the email address in your account

## Step 6: Common Solutions

### Solution 1: Add Your Email to ALLOWED_USERS

1. Go to Render → Your Service → Environment
2. Edit `ALLOWED_USERS`
3. Add your email: `your-actual-email@example.com`
4. Save and wait for redeploy

### Solution 2: Check for Typos

Make sure there are no typos in:
- Your email in the database
- Your email in ALLOWED_USERS
- Extra spaces or special characters

### Solution 3: Temporarily Disable Access Control

To test if access control is the issue:

1. Go to Render → Your Service → Environment
2. **Delete** the `ALLOWED_USERS` variable (or set it to empty)
3. Save and redeploy
4. Try logging in - if it works, the issue is with the ALLOWED_USERS configuration

### Solution 4: Create a New Account

If you can't remember your email or it's incorrect:

1. Temporarily remove `ALLOWED_USERS` from Render
2. Sign up with a new account using your correct email
3. Add that email to `ALLOWED_USERS`
4. Redeploy

## Still Having Issues?

Check the error message on the login page. In development mode, it will show:
- Your email address
- The list of authorized emails
- This helps you see exactly what's being compared

If you see "Access denied" but your email should be authorized, double-check:
1. The exact email address (including any dots, dashes, or special characters)
2. That there are no extra spaces in ALLOWED_USERS
3. That the environment variable was saved and the service redeployed

