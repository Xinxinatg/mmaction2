# Copyright (c) OpenMMLab. All rights reserved.
from unittest import TestCase

import numpy as np
import torch

from mmaction.evaluation import AccMetric, ConfusionMatrix
from mmaction.registry import METRICS
from mmaction.structures import ActionDataSample


def generate_data(num_classes=5, random_label=False):
    data_batch = []
    data_samples = []
    for i in range(num_classes * 10):
        logit = torch.randn(num_classes)
        if random_label:
            label = torch.randint(num_classes, size=[])
        else:
            label = torch.tensor(logit.argmax().item())
        data_sample = dict(
            pred_scores=dict(item=logit), gt_labels=dict(item=label))
        data_samples.append(data_sample)
    return data_batch, data_samples


def test_accmetric():
    num_classes = 32
    metric = AccMetric(
        metric_list=('top_k_accuracy', 'mean_class_accuracy',
                     'mmit_mean_average_precision', 'mean_average_precision'),
        num_classes=num_classes)
    data_batch, predictions = generate_data(
        num_classes=num_classes, random_label=True)
    metric.process(data_batch, predictions)
    eval_results = metric.compute_metrics(metric.results)
    assert 0.0 <= eval_results['top1'] <= eval_results['top5'] <= 1.0
    assert 0.0 <= eval_results['mean1'] <= 1.0
    metric.results.clear()

    data_batch, predictions = generate_data(
        num_classes=num_classes, random_label=False)
    metric.process(data_batch, predictions)
    eval_results = metric.compute_metrics(metric.results)
    assert eval_results['top1'] == eval_results['top5'] == 1.0
    assert eval_results['mean1'] == 1.0
    assert eval_results['mmit_mean_average_precision'] == 1.0
    return


class TestConfusionMatrix(TestCase):

    def test_evaluate(self):
        """Test using the metric in the same way as Evalutor."""
        pred = [
            ActionDataSample().set_pred_score(i).set_pred_label(
                j).set_gt_labels(k).to_dict() for i, j, k in zip([
                    torch.tensor([0.7, 0.0, 0.3]),
                    torch.tensor([0.5, 0.2, 0.3]),
                    torch.tensor([0.4, 0.5, 0.1]),
                    torch.tensor([0.0, 0.0, 1.0]),
                    torch.tensor([0.0, 0.0, 1.0]),
                    torch.tensor([0.0, 0.0, 1.0]),
                ], [0, 0, 1, 2, 2, 2], [0, 0, 1, 2, 1, 0])
        ]

        # Test with score (use score instead of label if score exists)
        metric = METRICS.build(dict(type='ConfusionMatrix'))
        metric.process(None, pred)
        res = metric.evaluate(6)
        self.assertIsInstance(res, dict)
        self.assertTensorEqual(
            res['confusion_matrix/result'],
            torch.tensor([
                [2, 0, 1],
                [0, 1, 1],
                [0, 0, 1],
            ]))

        # Test with label
        for sample in pred:
            del sample['pred_scores']
        metric = METRICS.build(dict(type='ConfusionMatrix'))
        metric.process(None, pred)
        with self.assertRaisesRegex(AssertionError,
                                    'Please specify the `num_classes`'):
            metric.evaluate(6)

        metric = METRICS.build(dict(type='ConfusionMatrix', num_classes=3))
        metric.process(None, pred)
        self.assertIsInstance(res, dict)
        self.assertTensorEqual(
            res['confusion_matrix/result'],
            torch.tensor([
                [2, 0, 1],
                [0, 1, 1],
                [0, 0, 1],
            ]))

    def test_calculate(self):
        y_true = np.array([0, 0, 1, 2, 1, 0])
        y_label = torch.tensor([0, 0, 1, 2, 2, 2])
        y_score = [
            [0.7, 0.0, 0.3],
            [0.5, 0.2, 0.3],
            [0.4, 0.5, 0.1],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],
        ]

        # Test with score
        cm = ConfusionMatrix.calculate(y_score, y_true)
        self.assertIsInstance(cm, torch.Tensor)
        self.assertTensorEqual(
            cm, torch.tensor([
                [2, 0, 1],
                [0, 1, 1],
                [0, 0, 1],
            ]))

        # Test with label
        with self.assertRaisesRegex(AssertionError,
                                    'Please specify the `num_classes`'):
            ConfusionMatrix.calculate(y_label, y_true)

        cm = ConfusionMatrix.calculate(y_label, y_true, num_classes=3)
        self.assertIsInstance(cm, torch.Tensor)
        self.assertTensorEqual(
            cm, torch.tensor([
                [2, 0, 1],
                [0, 1, 1],
                [0, 0, 1],
            ]))

        # Test with invalid inputs
        with self.assertRaisesRegex(TypeError, "<class 'str'> is not"):
            ConfusionMatrix.calculate(y_label, 'hi')

    def test_plot(self):
        import matplotlib.pyplot as plt

        cm = torch.tensor([[2, 0, 1], [0, 1, 1], [0, 0, 1]])
        fig = ConfusionMatrix.plot(cm, include_values=True, show=False)

        self.assertIsInstance(fig, plt.Figure)

    def assertTensorEqual(self,
                          tensor: torch.Tensor,
                          value: float,
                          msg=None,
                          **kwarg):
        tensor = tensor.to(torch.float32)
        value = torch.tensor(value).float()
        try:
            torch.testing.assert_allclose(tensor, value, **kwarg)
        except AssertionError as e:
            self.fail(self._formatMessage(msg, str(e)))
