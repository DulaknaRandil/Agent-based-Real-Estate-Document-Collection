"""
2captcha Service for CAPTCHA solving in Charleston County automation
"""
import logging
import asyncio
from typing import Dict, Optional
from twocaptcha import TwoCaptcha
from src.config import TWOCAPTCHA_API_KEY

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """2captcha service for solving CAPTCHAs during automation"""
    
    def __init__(self):
        self.solver = None
        self.initialize()
    
    def initialize(self):
        """Initialize 2captcha solver"""
        try:
            if not TWOCAPTCHA_API_KEY:
                raise ValueError("TWOCAPTCHA_API_KEY not found in environment")
            
            self.solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
            logger.info("2captcha service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize 2captcha: {e}")
    
    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2"""
        try:
            if not self.solver:
                raise ValueError("2captcha solver not initialized")
            
            logger.info(f"Solving reCAPTCHA v2 for site: {page_url}")
            
            # Submit captcha
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url
            )
            
            logger.info("reCAPTCHA v2 solved successfully")
            return result['code']
            
        except Exception as e:
            logger.error(f"Failed to solve reCAPTCHA v2: {e}")
            return None
    
    async def solve_recaptcha_v3(self, site_key: str, page_url: str, action: str = 'submit') -> Optional[str]:
        """Solve reCAPTCHA v3"""
        try:
            if not self.solver:
                raise ValueError("2captcha solver not initialized")
            
            logger.info(f"Solving reCAPTCHA v3 for site: {page_url}")
            
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url,
                version='v3',
                action=action
            )
            
            logger.info("reCAPTCHA v3 solved successfully")
            return result['code']
            
        except Exception as e:
            logger.error(f"Failed to solve reCAPTCHA v3: {e}")
            return None
    
    async def solve_image_captcha(self, image_path: str) -> Optional[str]:
        """Solve image-based CAPTCHA"""
        try:
            if not self.solver:
                raise ValueError("2captcha solver not initialized")
            
            logger.info(f"Solving image CAPTCHA: {image_path}")
            
            result = self.solver.normal(image_path)
            
            logger.info("Image CAPTCHA solved successfully")
            return result['code']
            
        except Exception as e:
            logger.error(f"Failed to solve image CAPTCHA: {e}")
            return None
    
    async def solve_text_captcha(self, text_question: str) -> Optional[str]:
        """Solve text-based CAPTCHA"""
        try:
            if not self.solver:
                raise ValueError("2captcha solver not initialized")
            
            logger.info(f"Solving text CAPTCHA: {text_question}")
            
            result = self.solver.text(text_question)
            
            logger.info("Text CAPTCHA solved successfully")
            return result['code']
            
        except Exception as e:
            logger.error(f"Failed to solve text CAPTCHA: {e}")
            return None
    
    async def detect_and_solve_captcha(self, page, page_url: str) -> Optional[str]:
        """Detect and solve any CAPTCHA on the current page"""
        try:
            # Check for reCAPTCHA v2
            recaptcha_v2 = await page.querySelector('.g-recaptcha')
            if recaptcha_v2:
                site_key = await page.evaluate(
                    '() => document.querySelector(".g-recaptcha").getAttribute("data-sitekey")'
                )
                if site_key:
                    return await self.solve_recaptcha_v2(site_key, page_url)
            
            # Check for reCAPTCHA v3
            recaptcha_v3 = await page.querySelector('[data-action]')
            if recaptcha_v3:
                site_key = await page.evaluate(
                    '() => document.querySelector("[data-sitekey]").getAttribute("data-sitekey")'
                )
                action = await page.evaluate(
                    '() => document.querySelector("[data-action]").getAttribute("data-action")'
                )
                if site_key:
                    return await self.solve_recaptcha_v3(site_key, page_url, action or 'submit')
            
            # Check for image CAPTCHA
            captcha_image = await page.querySelector('img[src*="captcha"], img[alt*="captcha"]')
            if captcha_image:
                # Download and solve image captcha
                logger.info("Image CAPTCHA detected - manual intervention may be required")
                return None
            
            logger.info("No CAPTCHA detected on page")
            return "no_captcha_found"
            
        except Exception as e:
            logger.error(f"Failed to detect/solve CAPTCHA: {e}")
            return None
    
    def get_balance(self) -> float:
        """Get 2captcha account balance"""
        try:
            if not self.solver:
                return 0.0
            
            balance = self.solver.balance()
            logger.info(f"2captcha balance: ${balance}")
            return float(balance)
            
        except Exception as e:
            logger.error(f"Failed to get 2captcha balance: {e}")
            return 0.0
