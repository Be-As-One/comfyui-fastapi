#!/usr/bin/env python3
"""
Face Swap Processor
Handles face swap task processing via FaceFusion API integration
"""

from typing import Dict, Any, Optional
from loguru import logger
from services.face_swap_service import (
    face_swap_service, FaceSwapRequest, FaceSwapResponse
)
from core.storage.manager import storage_manager


class FaceSwapProcessor:
    """Processor for face swap tasks using FaceFusion API"""

    def __init__(self):
        self.service = face_swap_service

    async def process_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a face swap task"""
        logger.info(f"Processing face swap task with data: {input_data}")

        try:
            # Extract task parameters from unified input_data format
            source_url = input_data.get("source_url")
            target_url = input_data.get("target_url")
            resolution = input_data.get("resolution", "1024x1024")
            model = input_data.get("model", "inswapper_128_fp16")

            if not source_url or not target_url:
                raise ValueError("Both source_url and target_url are required")

            # Create face swap request
            request = FaceSwapRequest(
                source_url=source_url,
                target_url=target_url,
                resolution=resolution,
                model=model
            )

            # Process face swap
            result = await self.service.process_face_swap(request)

            if result.status == "success":
                # Upload result to storage if configured
                final_url = await self._upload_result(result)

                return {
                    "status": "success",
                    "result": {
                        "output_url": final_url or result.output_path,
                        "local_path": result.output_path,
                        "processing_time": result.processing_time,
                        "job_id": result.job_id,
                        "metadata": result.metadata or {}
                    }
                }
            else:
                return {
                    "status": "failed",
                    "error": result.error or "Face swap processing failed",
                    "processing_time": result.processing_time
                }

        except Exception as e:
            logger.error(f"Face swap processing error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _upload_result(self, result: FaceSwapResponse) -> Optional[str]:
        """Upload face swap result to configured storage"""
        if not result.output_path:
            return None

        try:
            # Construct full local path
            local_path = f"/Users/hzy/Code/zhuilai/video-faceswap{result.output_path}"

            # Determine content type
            content_type = "image/jpeg"
            if result.metadata and result.metadata.get("file_type") == "video":
                content_type = "video/mp4"

            # Upload to storage
            upload_result = await storage_manager.upload_file(
                local_path,
                content_type=content_type
            )

            if upload_result and upload_result.get("url"):
                logger.info(
                    f"Face swap result uploaded to: {upload_result['url']}")
                return upload_result["url"]
            else:
                logger.warning("Failed to upload face swap result to storage")
                return None

        except Exception as e:
            logger.error(f"Error uploading face swap result: {e}")
            return None


# Global processor instance
face_swap_processor = FaceSwapProcessor()
