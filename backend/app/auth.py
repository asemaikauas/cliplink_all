"""
Clerk JWT Authentication for Cliplink Backend

This module provides JWT token verification using Clerk's JWKS endpoint
and user management with SQLAlchemy.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import User
from .database import get_db

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()

# Clerk configuration
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")
JWKS_URL = os.getenv("JWKS_URL") or f"https://{CLERK_DOMAIN}/.well-known/jwks.json"

if not CLERK_DOMAIN:
    logger.warning("CLERK_DOMAIN environment variable not set")


def get_jwks_client() -> PyJWKClient:
    """Get PyJWKClient for Clerk JWKS endpoint"""
    return PyJWKClient(JWKS_URL)


def verify_clerk_token(token: str) -> dict:
    """
    Verify and decode Clerk JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        jwk_client = get_jwks_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        
        # Decode token without audience verification (as requested)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        
        logger.debug(f"Successfully verified token for user: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object from database
        
    Raises:
        HTTPException: 401 if token is invalid or user cannot be found/created
    """
    token = credentials.credentials
    
    try:
        # Verify and decode the JWT token
        payload = verify_clerk_token(token)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user information from token
    clerk_id: str = payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing sub claim in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user data from various possible claim locations
    email = (
        payload.get("email") or 
        payload.get("primary_email_address", {}).get("email_address") or
        payload.get("email_addresses", [{}])[0].get("email_address")
    )
    
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    
    try:
        # Try to find existing user by clerk_id
        query = select(User).where(User.clerk_id == clerk_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            # If not found by clerk_id, try to find by email
            if email:
                email_query = select(User).where(User.email == email)
                email_result = await db.execute(email_query)
                user_by_email = email_result.scalar_one_or_none()
                if user_by_email:
                    # Update clerk_id if needed
                    if not user_by_email.clerk_id or user_by_email.clerk_id != clerk_id:
                        user_by_email.clerk_id = clerk_id
                        if first_name and user_by_email.first_name != first_name:
                            user_by_email.first_name = first_name
                        if last_name and user_by_email.last_name != last_name:
                            user_by_email.last_name = last_name
                        await db.commit()
                        await db.refresh(user_by_email)
                        logger.info(f"Updated existing user with new clerk_id: {user_by_email.email} (clerk_id: {clerk_id})")
                    return user_by_email
            # Create new user if not found by clerk_id or email
            user = User(
                clerk_id=clerk_id,
                email=email or f"{clerk_id}@clerk.local",  # Fallback email
                first_name=first_name,
                last_name=last_name,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"Created new user: {user.email} (clerk_id: {clerk_id})")
        else:
            # Check if user data needs updating
            updated = False
            updates = {}
            if email and user.email != email:
                updates["email"] = email
                updated = True
            if first_name and user.first_name != first_name:
                updates["first_name"] = first_name
                updated = True
            if last_name and user.last_name != last_name:
                updates["last_name"] = last_name
                updated = True
            if updated:
                # Update user data
                for field, value in updates.items():
                    setattr(user, field, value)
                await db.commit()
                await db.refresh(user)
                logger.info(f"Updated user data for {user.email}: {updates}")
        return user
        
    except Exception as e:
        logger.error(f"Database error while handling user {clerk_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    FastAPI dependency for optional authentication
    
    Args:
        db: Database session
        credentials: Optional bearer token
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        # Use the main authentication function
        return await get_current_user(credentials, db)
    except HTTPException:
        # If authentication fails, return None instead of raising
        return None


def require_role(required_role: str):
    """
    Placeholder for role-based access control
    Currently not implemented - all authenticated users have access
    
    Args:
        required_role: Required role string
        
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        # TODO: Implement role checking when roles are added to User model
        # For now, just return the user if they're authenticated
        return user
    
    return role_checker


# Convenience dependency for admin-only endpoints
get_admin_user = require_role("admin") 