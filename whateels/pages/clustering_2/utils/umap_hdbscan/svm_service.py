import numpy as np

from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.svm import SVC


class SVMService:
    """Encapsulates SVM/SGD training and outlier reassignment for clustering_2."""

    def __init__(self, data_3d: np.ndarray):
        self._data = np.array(data_3d)

    def train_svm_from_hdbscan_labels(
        self,
        hdbscan_labels: np.ndarray,
        kernel: str,
        c_value: float = 1.0,
        gamma: str | float | None = None,
        coef0: float | None = None,
        degree: int = 3,
        test_size: float = 0.25,
        cv: int = 10,
        probability: bool = False,
        min_size: int = 400,
        random_state: int = 42,
    ) -> dict:
        """Train a classifier from HDBSCAN labels using class-balanced sampling."""
        samples, labels, class_map, class_counts = self._build_balanced_samples(
            hdbscan_labels=hdbscan_labels,
            min_size=min_size,
            random_state=random_state,
        )

        model, cv_scores, cv_mean, test_accuracy = self._train_and_evaluate(
            samples=samples,
            labels=labels,
            kernel=kernel,
            c_value=c_value,
            gamma=gamma,
            coef0=coef0,
            degree=degree,
            test_size=test_size,
            cv=cv,
            probability=probability,
            random_state=random_state,
        )

        return {
            "model": model,
            "samples": samples,
            "labels": labels,
            "class_map": class_map,
            "class_counts": class_counts,
            "cv_scores": cv_scores,
            "cv_mean": cv_mean,
            "test_accuracy": test_accuracy,
        }

    def reassign_outliers(
        self,
        hdbscan_labels: np.ndarray,
        model,
        class_map: dict[int, int],
        outlier_label: int = -1,
    ) -> tuple[np.ndarray, int]:
        """Predict and reassign outlier labels using a trained classifier."""
        labels_flat = np.array(hdbscan_labels).reshape(-1)
        outlier_mask = labels_flat == int(outlier_label)

        if not np.any(outlier_mask):
            return labels_flat.copy(), 0

        flat_data = self._data.reshape(-1, self._data.shape[-1])
        outlier_spectra = flat_data[outlier_mask]
        predicted_model_labels = model.predict(outlier_spectra)

        mapped_cluster_labels = np.array(
            [class_map[int(model_label)] for model_label in predicted_model_labels],
            dtype=int,
        )

        reassigned = labels_flat.copy()
        reassigned[outlier_mask] = mapped_cluster_labels
        return reassigned, int(outlier_spectra.shape[0])

    def _build_balanced_samples(
        self,
        hdbscan_labels: np.ndarray,
        min_size: int,
        random_state: int,
    ) -> tuple[np.ndarray, np.ndarray, dict[int, int], dict[int, int]]:
        """Create class-balanced samples from non-outlier HDBSCAN clusters."""
        labels_flat = np.array(hdbscan_labels).reshape(-1)
        flat_data = self._data.reshape(-1, self._data.shape[-1])

        unique_labels = np.unique(labels_flat)
        valid_cluster_labels = [int(label) for label in unique_labels if int(label) != -1]
        if not valid_cluster_labels:
            raise ValueError("No non-outlier HDBSCAN clusters available to train SVM.")

        rng = np.random.default_rng(seed=int(random_state))

        sampled_blocks: list[np.ndarray] = []
        sampled_labels: list[np.ndarray] = []
        class_map: dict[int, int] = {}
        class_counts: dict[int, int] = {}

        model_class_idx = 0
        for cluster_label in sorted(valid_cluster_labels):
            cluster_mask = labels_flat == cluster_label
            cluster_spectra = flat_data[cluster_mask]
            cluster_count = int(cluster_spectra.shape[0])
            class_counts[cluster_label] = cluster_count

            if cluster_count < int(min_size):
                continue

            selected_idx = rng.choice(cluster_count, size=int(min_size), replace=False)
            sampled_cluster = cluster_spectra[selected_idx]

            sampled_blocks.append(sampled_cluster)
            sampled_labels.append(np.full(int(min_size), model_class_idx, dtype=int))
            class_map[model_class_idx] = cluster_label
            model_class_idx += 1

        if not sampled_blocks:
            raise ValueError(
                "No HDBSCAN clusters have enough points for balanced SVM training. "
                f"Increase cluster sizes or lower min_size (current={min_size})."
            )

        samples = np.vstack(sampled_blocks)
        labels = np.concatenate(sampled_labels)
        return samples, labels, class_map, class_counts

    def _train_and_evaluate(
        self,
        samples: np.ndarray,
        labels: np.ndarray,
        kernel: str,
        c_value: float,
        gamma: str | float | None,
        coef0: float | None,
        degree: int,
        test_size: float,
        cv: int,
        probability: bool,
        random_state: int,
    ):
        """Split data, run CV when possible, train and evaluate the classifier."""
        if labels.size == 0:
            raise ValueError("Cannot train SVM with empty labels.")

        unique_labels, counts = np.unique(labels, return_counts=True)
        if unique_labels.size < 2:
            raise ValueError("Need at least two classes to train SVM.")

        stratify = labels if np.min(counts) > 1 else None

        x_train, x_test, y_train, y_test = train_test_split(
            samples,
            labels,
            test_size=float(test_size),
            random_state=int(random_state),
            stratify=stratify,
        )

        model = self._build_model(
            kernel=kernel,
            c_value=c_value,
            gamma=gamma,
            coef0=coef0,
            degree=degree,
            probability=probability,
            random_state=random_state,
        )

        cv_scores = np.array([])
        cv_mean = None
        y_train_unique, y_train_counts = np.unique(y_train, return_counts=True)
        max_cv = int(np.min(y_train_counts)) if y_train_unique.size > 1 else 0
        requested_cv = int(cv)
        cv_to_use = min(requested_cv, max_cv)

        if cv_to_use >= 2:
            cv_scores = cross_val_score(model, x_train, y_train, cv=cv_to_use)
            cv_mean = float(np.mean(cv_scores))

        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        test_accuracy = float(accuracy_score(y_test, y_pred))

        return model, cv_scores, cv_mean, test_accuracy

    def _build_model(
        self,
        kernel: str,
        c_value: float,
        gamma: str | float | None,
        coef0: float | None,
        degree: int,
        probability: bool,
        random_state: int,
    ):
        """Build the configured classifier, supporting notebook-compatible kernels."""
        normalized_kernel = str(kernel).lower().strip()
        if normalized_kernel == "sdg":
            normalized_kernel = "sgd"

        if normalized_kernel == "sgd":
            return SGDClassifier(class_weight="balanced", random_state=int(random_state))

        svc_kwargs = {
            "C": float(c_value),
            "probability": bool(probability),
            "decision_function_shape": "ovr",
            "class_weight": "balanced",
        }

        if normalized_kernel == "cosine":
            return SVC(kernel=cosine_similarity, **svc_kwargs)

        if normalized_kernel in {"linear", "rbf", "poly", "sigmoid"}:
            if normalized_kernel in {"rbf", "poly", "sigmoid"}:
                svc_kwargs["gamma"] = self._parse_gamma(gamma)
            if normalized_kernel in {"poly", "sigmoid"} and coef0 is not None:
                svc_kwargs["coef0"] = float(coef0)
            if normalized_kernel == "poly":
                svc_kwargs["degree"] = int(degree)

            return SVC(kernel=normalized_kernel, **svc_kwargs)

        raise ValueError(
            "kernel must be one of ['linear', 'rbf', 'poly', 'sigmoid', 'cosine', 'sgd']"
        )

    @staticmethod
    def _parse_gamma(gamma: str | float | None):
        """Normalize gamma values accepted in UI/modal."""
        if gamma is None:
            return "scale"

        if isinstance(gamma, (int, float)):
            return float(gamma)

        text = str(gamma).strip().lower()
        if text in {"", "none", "default", "scale"}:
            return "scale"
        if text == "auto":
            return "auto"

        return float(text)
