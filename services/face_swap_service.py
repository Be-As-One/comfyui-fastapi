#!/usr/bin/env python3
"""
Face Swap Service - Integration with FaceFusion API
Provides face swap functionality via HTTP API calls to co-located service
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger
from config.settings import (
    FACE_SWAP_API_URL, FACE_SWAP_TIMEOUT, FACE_SWAP_RETRY_COUNT
)


class FaceSwapRequest(BaseModel):
    """Face swap processing request"""
    source_url: str = Field(...,
                            description="URL of the source image (face to swap)")
    target_url: str = Field(...,
                            description="URL of the target image/video")
    resolution: str = Field("1024x1024", description="Output resolution")
    model: str = Field("inswapper_128_fp16",
                       description="Face swapper model to use")


class FaceSwapResponse(BaseModel):
    """Face swap processing response"""
    status: str
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FaceSwapService:
    """Service for face swap operations via FaceFusion API"""

    def __init__(self):
        self.base_url = FACE_SWAP_API_URL
        self.timeout = float(FACE_SWAP_TIMEOUT)
        self.retry_count = FACE_SWAP_RETRY_COUNT

    async def health_check(self) -> bool:
        """Check if face swap service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Face swap service health check failed: {e}")
            return False

    async def process_face_swap(self,
                                request: FaceSwapRequest) -> FaceSwapResponse:
        """Process face swap request via API call"""
        logger.info(f"Processing face swap: {request.source_url} -> "
                    f"{request.target_url}")

        # Check service availability
        if not await self.health_check():
            raise Exception("Face swap service is not available")

        # Prepare request data
        request_data = {
            "source_url": request.source_url,
            "target_url": request.target_url,
            "resolution": request.resolution,
            "model": request.model
        }

        # Make API call with retries
        for attempt in range(self.retry_count):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/process",
                        json=request_data
                    )

                    if response.status_code == 200:
                        result_data = response.json()
                        return FaceSwapResponse(**result_data)
                    else:
                        error_msg = (f"Face swap API returned "
                                     f"{response.status_code}: {response.text}")
                        logger.error(error_msg)
                        raise Exception(error_msg)

            except httpx.TimeoutException:
                logger.warning(f"Face swap request timeout "
                               f"(attempt {attempt + 1}/{self.retry_count})")
                if attempt == self.retry_count - 1:
                    raise Exception("Face swap service timeout")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                logger.error(f"Face swap API call failed "
                             f"(attempt {attempt + 1}/{self.retry_count}): {e}")
                if attempt == self.retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def get_service_info(self) -> Dict[str, Any]:
        """Get face swap service information"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error":
                            f"Service returned {response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to get face swap service info: {e}")
            return {"error": str(e)}


# Global service instance
face_swap_service = FaceSwapService()
