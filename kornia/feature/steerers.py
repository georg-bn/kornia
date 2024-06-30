from typing import Dict

import torch

from kornia.core import Module, Tensor
from kornia.utils.helpers import map_location_to_cpu

class DiscreteSteerer(Module):
    """Module for discrete rotation steerers.

    A steerer rotates keypoint descriptions in latent space as if they were obtained from rotated images.

    Args:
        generator: [N, N] tensor where N is the descriptor dimension.

    Example:
        >>> desc = torch.randn(512, 128)
        >>> generator = torch.randn(128, 128)
        >>> steerer = DiscreteSteerer(generator)
        >>> steered_desc = steerer.steer_descriptions(desc, steerer_power=3, normalize=True)  # steer 3 times
    """
    def __init__(self, generator: Tensor) -> None:
        super().__init__()
        self.generator = torch.nn.Parameter(generator)

    def forward(self, x: Tensor) -> Tensor:
        return torch.nn.functional.linear(x, self.generator)

    def steer_descriptions(
        self,
        descriptions: Tensor,
        steerer_power: int = 1,
        normalize: bool = False,
    ) -> Tensor:
        for _ in range(steerer_power):
            descriptions = self.forward(descriptions)
        if normalize:
            descriptions = torch.nn.functional.normalize(descriptions, dim=-1)
        return descriptions

    @classmethod
    def from_pretrained(
        cls,
        generator_type: str = "C4",
        steerer_order: int = 8,
    ) -> Module:
        r"""Loads a steerer for pretrained DeDoDe descriptors from the paper https://arxiv.org/abs/2312.02152.

        Args:
            generator_type: The type of steerer generator.
                One of 'C4', 'SO2', default is 'C4'.
                These can be used with the DeDoDe descriptors with C4 or SO2 in the name respectively.
            steerer_order: The discretisation order for SO2-steerers (NOT used for C4-steerers).

        Returns:
            The pretrained model.
        """
        descriptor_dim = 256
        if generator_type == "C4":
            generator = torch.block_diag(
                *(
                    torch.tensor([[0., 1, 0, 0],
                                  [0, 0, 1, 0],
                                  [0, 0, 0, 1],
                                  [1, 0, 0, 0]])
                    for _ in range(descriptor_dim // 4)
                )
            )
            return DiscreteSteerer(generator).eval()
        elif generator_type == "SO2":
            lie_generator = torch.block_diag(
                torch.zeros(
                    [descriptor_dim - 12 * descriptor_dim // 14,
                     descriptor_dim - 12 * descriptor_dim // 14],
                ),
                *(
                    torch.tensor([[0., j],
                                  [-j, 0]])
                    for j in range(1, 7)
                    for _ in range(descriptor_dim // 14)
                ),
            )
            generator = torch.matrix_exp((2 * 3.14159 / steerer_order) * lie_generator)
            return DiscreteSteerer(generator).eval()
        else:
            raise ValueError
