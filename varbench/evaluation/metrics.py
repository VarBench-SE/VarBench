from datasets import Dataset
from loguru import logger
import torch.utils
import torch.utils

from varbench.evaluation.clip_comparer import ClipComparer
from varbench.evaluation.line_patch_scorer import compute_line_score
from varbench.utils.patches import patches


class Metric:
    def __init__(self, *args, **kwargs) -> None:
        """instantiates a metric"""
        pass

    def compute(self, dataset: Dataset) -> list[list[float]]:
        """computes the metric using the dataset
        The dataset should have columns: id,code,code_solution,predictions,patches,result_description,image_solution,image_input,images_result

        Args:
            dataset (Dataset): The dataset used to copute the metric on

        Returns:
            a list of list of metrics evaluated on the instances in the dataset
        """
        pass


class PatchMetric(Metric):
    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing patch_score")
        inputs = dataset["code"]
        predictions = dataset["predictions"]
        patch = dataset["patch"]
        individual_patches = [patches(i, p) for i, p in zip(inputs, predictions)]
        print(individual_patches[0])
        print(patch)
        individual_patches_scores = [
            [int(computed_patch == p) * 100.0 for computed_patch in i]
            for i, p in zip(individual_patches, patch)
        ]
        return individual_patches_scores


class LineMetric(Metric):
    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing line_score")
        inputs = dataset["code"]
        predictions = dataset["predictions"]
        patch = dataset["patch"]
        individual_patches = [patches(i, p) for i, p in zip(inputs, predictions)]
        individual_lines_scores = compute_line_score(individual_patches, patch)

        return individual_lines_scores


class ClipImageMetric(Metric):
    def __init__(self, clip_comparer: ClipComparer = None, *args, **kwargs) -> None:
        self.clip_comparer = clip_comparer
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing clip image to image similarity scores")
        logger.info(dataset["images_result"])
        image_result = dataset["images_result"]
        image_solution = dataset["image_solution"]
        individual_image_scores = self.clip_comparer.image_similarities(
            image_result, image_solution
        )
        return individual_image_scores


class ClipTextMetric(Metric):
    def __init__(self, clip_comparer: ClipComparer = None, *args, **kwargs) -> None:
        self.clip_comparer = clip_comparer
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing clip text to image similarity scores")
        image_result = dataset["images_result"]
        result_description = dataset["result_description"]
        individual_text_scores = self.clip_comparer.text_similarities(
            image_result, result_description
        )
        return individual_text_scores


class BleuMetric(Metric):
    def __init__(self, *args, **kwargs) -> None:
        from sacrebleu import BLEU

        self.bleu = BLEU()
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing bleu_score")
        all_predictions = dataset["predictions"]
        solutions = dataset["code_solution"]

        bleu_scores = [
            [
                self.bleu.sentence_score(row_prediction, [solution]).score
                for row_prediction in predictions
            ]
            for predictions, solution in zip(all_predictions, solutions)
        ]

        return bleu_scores


class ChrfMetric(Metric):
    def __init__(self, *args, **kwargs) -> None:
        from sacrebleu import CHRF

        self.chrf = CHRF()
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing bleu_score")
        all_predictions = dataset["predictions"]
        solutions = dataset["code_solution"]

        chrf_scores = [
            [
                self.chrf.sentence_score(row_prediction, [solution]).score
                for row_prediction in predictions
            ]
            for predictions, solution in zip(all_predictions, solutions)
        ]

        return chrf_scores


class TERMetric(Metric):
    def __init__(self, *args, **kwargs) -> None:
        from sacrebleu import TER

        self.ter = TER()
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        logger.info("Computing bleu_score")
        all_predictions = dataset["predictions"]
        solutions = dataset["code_solution"]

        ter_inverted_scores = [
            [
                100 - self.ter.sentence_score(row_prediction, [solution]).score
                for row_prediction in predictions
            ]
            for predictions, solution in zip(all_predictions, solutions)
        ]

        return ter_inverted_scores


import cv2
import numpy as np


class FeatureMatchMetric(Metric):

    def __init__(self, *args, **kwargs) -> None:

        self.sift = cv2.SIFT.create()
        self.bf_matcher = cv2.BFMatcher()
        self.threshold = 0.5
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        def _convert(image):
            return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)

        def _filter_matches(matches):
            filtered_matches = []
            for m, n in matches:
                if m.distance < self.threshold * n.distance:
                    filtered_matches.append(m)
            return filtered_matches

        def compare_sift_brut(
            reference: cv2.typing.MatLike, predictions: list[cv2.typing.MatLike]
        ) -> list[float]:
            ref_features = self.sift.detectAndCompute(reference, None)[1]
            predictions_features = [
                self.sift.detectAndCompute(prediction, None)[1]
                for prediction in predictions
            ]
            ref_own_matches = _filter_matches(
                self.bf_matcher.knnMatch(ref_features, ref_features, k=2)
            )  # theoric maximum amount of matches that a image can have with the reference
            pred_ref_matches = [
                _filter_matches(
                    self.bf_matcher.knnMatch(pred_features, ref_features, k=2)
                )
                for pred_features in predictions_features
            ]

            nb_max_matches = len(ref_own_matches)

            pred_scores = [
                100.0 * (len(pred_matches) / nb_max_matches)
                for pred_matches in pred_ref_matches
            ]

            return pred_scores

        # converting to cv2 images
        reference_images = [
            _convert(ref_image) for ref_image in dataset["image_solution"]
        ]
        predictions_images = [
            [_convert(result_image) for result_image in row_images]
            for row_images in dataset["images_result"]
        ]

        return [
            compare_sift_brut(ref_image, predictions)
            for ref_image, predictions in zip(reference_images, predictions_images)
        ]


class LPIPSMetric(Metric):
    def __init__(self, *args, **kwargs) -> None:
        import torchvision.transforms as transforms
        import lpips

        self.transform = transforms.Compose(
            [
                transforms.Resize((64, 64)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5)
                ),  # Normalize to [-1, 1]
            ]
        )
        self.loss_fn_alex = lpips.LPIPS(net="alex")
        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:
        references = dataset["image_solution"]
        predictions = dataset["images_result"]
        scores = []

        for reference_image, predicted_images in zip(references, predictions):
            # Transform the reference and predictions
            reference_tensor = self.transform(reference_image.convert("RGB")).unsqueeze(
                0
            )
            # Compute loss for each predicted image individually
            individual_scores = [
                100.0
                - 100.0
                * self.loss_fn_alex(
                    reference_tensor, self.transform(img.convert("RGB")).unsqueeze(0)
                ).item()
                for img in predicted_images
            ]
            scores.append(individual_scores)

        return scores


class PSNRMetric(Metric):
    def compute(self, dataset: Dataset) -> list[list[float]]:

        def PSNR(original, compressed):
            mse = np.mean((original - compressed) ** 2)
            if mse == 0:
                return 100
            max_pixel = 255.0
            psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
            return psnr

        references = dataset["image_solution"]
        predictions = dataset["images_result"]
        references = [np.array(pil_image.convert("RGB")) for pil_image in references]
        predictions = [
            [np.array(pil_image.convert("RGB")) for pil_image in pil_images]
            for pil_images in predictions
        ]

        return [
            [PSNR(reference, prediction) for prediction in row_predictions]
            for reference, row_predictions in zip(references, predictions)
        ]


class MSSSIMMetric(Metric):
    def __init__(self, *args, **kwargs) -> None:
        from pytorch_msssim import MS_SSIM
        from torchvision.transforms import ToTensor

        self.totensor = ToTensor()
        self.ms_ssim_module = MS_SSIM(data_range=1, size_average=False, channel=3)

        super().__init__(*args, **kwargs)

    def compute(self, dataset: Dataset) -> list[list[float]]:

        references = dataset["image_solution"]
        predictions = dataset["images_result"]
        references = [
            self.totensor(pil_image.convert("RGB")).unsqueeze(0)
            for pil_image in references
        ]
        predictions = [
            [
                self.totensor(pil_image.convert("RGB")).unsqueeze(0)
                for pil_image in pil_images
            ]
            for pil_images in predictions
        ]

        return [
            [
                100.0 * self.ms_ssim_module(reference, prediction).item()
                for prediction in row_predictions
            ]
            for reference, row_predictions in zip(references, predictions)
        ]


def instantiate_metrics(metric_names: list[str]) -> list[Metric]:

    metric_map = {
        "patch": PatchMetric,
        "line": LineMetric,
        "clipImage": ClipImageMetric,
        "clipText": ClipTextMetric,
        "bleu": BleuMetric,
        "chrf": ChrfMetric,
        "TER": TERMetric,
        "featureMatch": FeatureMatchMetric,
        "LPIPS": LPIPSMetric,
        "psnr": PSNRMetric,
        "msssim": MSSSIMMetric,
    }
    metrics: set[Metric] = set([metric_map[m_name] for m_name in set(metric_names)])
    if set([ClipImageMetric, ClipTextMetric]) & metrics:
        clip_comparer = ClipComparer()
    return [metric(clip_comparer) for metric in metrics]


import math


class MetricPolicy:
    @staticmethod
    def mathematical_average(values: list[float], weights: list[float] = None) -> float:
        if weights is None:
            return sum(values) / len(values)
        return sum(v * w for v, w in zip(values, weights)) / sum(weights)

    @staticmethod
    def geometrical_average(values: list[float], weights: list[float] = None) -> float:
        if weights is None:
            return math.prod(values) ** (1 / len(values))
        total_weight = sum(weights)
        return math.prod(v ** (w / total_weight) for v, w in zip(values, weights))

    @staticmethod
    def harmonic_mean(values: list[float]) -> float:
        return len(values) / sum(1 / v for v in values)