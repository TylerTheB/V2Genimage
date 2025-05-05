#!/usr/bin/env python3
"""
Data models for Tensor Art API requests and responses.
These classes provide structured representations of API objects.
"""

from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field


@dataclass
class TextPrompt:
    """Represents a text prompt for image generation"""
    text: str


@dataclass
class DiffusionParams:
    """Parameters for the diffusion stage of image generation"""
    width: int = 512
    height: int = 512
    prompts: List[TextPrompt] = field(default_factory=list)
    negativePrompts: List[TextPrompt] = field(default_factory=list)
    sdModel: str = ""  # Model ID
    sdVae: str = "Automatic"
    sampler: str = "DPM++ 2M Karras"
    steps: int = 25
    cfgScale: float = 7.0
    clipSkip: int = 2
    denoisingStrength: float = 0.7
    lora: Dict[str, Any] = field(default_factory=dict)
    embedding: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputInitializeStage:
    """Input initialization stage of image generation"""
    type: str = "INPUT_INITIALIZE"
    inputInitialize: Dict[str, Any] = field(default_factory=lambda: {
        "seed": "-1",  # Random seed
        "count": 1
    })


@dataclass
class DiffusionStage:
    """Diffusion stage of image generation"""
    type: str = "DIFFUSION"
    diffusion: DiffusionParams = field(default_factory=DiffusionParams)


@dataclass
class TextToImageRequest:
    """A complete text-to-image job request"""
    requestId: str
    stages: List[Union[InputInitializeStage, DiffusionStage]] = field(default_factory=list)

    @classmethod
    def create(cls, request_id: str, prompt: str, model_id: str,
               width: int = 512, height: int = 512, steps: int = 25,
               sampler: str = "DPM++ 2M Karras", negative_prompt: str = ""):
        """Factory method to create a text-to-image request"""
        # Create prompts
        prompts = [TextPrompt(text=prompt)]
        negative_prompts = [TextPrompt(text=negative_prompt)] if negative_prompt else []
        
        # Create diffusion parameters
        diffusion_params = DiffusionParams(
            width=width,
            height=height,
            prompts=prompts,
            negativePrompts=negative_prompts,
            sdModel=model_id,
            steps=steps,
            sampler=sampler
        )
        
        # Create stages
        input_init = InputInitializeStage()
        diffusion = DiffusionStage(diffusion=diffusion_params)
        
        return cls(
            requestId=request_id,
            stages=[input_init, diffusion]
        )


@dataclass
class JobResource:
    """Represents a resource (like an image) from a job response"""
    url: str
    type: str
    name: str


@dataclass
class JobResponse:
    """Response from a job creation or status request"""
    jobId: str
    status: str
    progress: Optional[float] = None
    credits: Optional[float] = None
    resources: List[JobResource] = field(default_factory=list)
    message: Optional[str] = None
    createdAt: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create a JobResponse from a dictionary"""
        resources = []
        if 'resources' in data and data['resources']:
            for res in data['resources']:
                resources.append(JobResource(
                    url=res.get('url', ''),
                    type=res.get('type', ''),
                    name=res.get('name', '')
                ))
        
        return cls(
            jobId=data.get('jobId', ''),
            status=data.get('status', ''),
            progress=data.get('progress'),
            credits=data.get('credits'),
            resources=resources,
            message=data.get('message'),
            createdAt=data.get('createdAt')
        )


@dataclass
class ModelInfo:
    """Information about a model"""
    id: str
    name: str
    type: str
    hash: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    downloadUrl: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    createdAt: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create a ModelInfo from a dictionary"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            type=data.get('type', ''),
            hash=data.get('hash'),
            description=data.get('description'),
            imageUrl=data.get('imageUrl'),
            downloadUrl=data.get('downloadUrl'),
            tags=data.get('tags', []),
            createdAt=data.get('createdAt')
        )
