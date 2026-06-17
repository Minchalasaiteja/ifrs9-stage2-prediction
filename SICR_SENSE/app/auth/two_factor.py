import pyotp
import qrcode
import io
import base64
from typing import Dict, Any, Optional
from ..database import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TwoFactorAuth:
    @staticmethod
    def generate_secret() -> str:
        """Generate new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(email: str, secret: str) -> str:
        """Generate QR code for Google Authenticator"""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            email,
            issuer_name="SICRSense"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    @staticmethod
    async def enable_2fa(user_id: str, secret: str) -> bool:
        """Enable 2FA for user"""
        try:
            await db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "two_factor_enabled": True,
                        "two_factor_secret": secret,
                        "two_factor_enabled_at": datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to enable 2FA: {e}")
            return False
    
    @staticmethod
    async def disable_2fa(user_id: str) -> bool:
        """Disable 2FA for user"""
        try:
            await db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {"two_factor_enabled": False},
                    "$unset": {"two_factor_secret": "", "two_factor_enabled_at": ""}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to disable 2FA: {e}")
            return False