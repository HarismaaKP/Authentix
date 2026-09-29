"""
AI product image verification for Authentix.

Pipeline:
1. Load the registered/original product image.
2. Load the customer-scanned product image.
3. Detect important visual features using ORB.
4. Match ORB descriptors using Hamming distance.
5. Apply Lowe's ratio test to remove weak matches.
6. Apply RANSAC homography to verify that matches have
   a consistent geometric relationship.
7. Calculate a similarity score.
8. Classify the product as:
       AUTHENTIC
       SUSPICIOUS
       COUNTERFEIT

This version does not use ResNet, PyTorch, or torchvision.
It is designed to run quickly on a normal computer.
"""

import cv2
import numpy as np


# =========================================================
# SETTINGS
# =========================================================

# Final score thresholds
# 78+     = AUTHENTIC
# 55-77.99 = SUSPICIOUS
# Below 55 = COUNTERFEIT

AUTHENTIC_THRESHOLD = 78
SUSPICIOUS_THRESHOLD = 55

# ORB settings
ORB_FEATURES = 2500

# Lowe ratio test
RATIO_TEST = 0.70

# Minimum number of good matches required
MIN_GOOD_MATCHES = 8

# Minimum number of RANSAC inliers required
MIN_INLIERS = 6


# =========================================================
# ORB INITIALIZATION
# =========================================================

_ORB = cv2.ORB_create(
    nfeatures=ORB_FEATURES,
    scaleFactor=1.2,
    nlevels=8,
    edgeThreshold=31,
    firstLevel=0,
    WTA_K=2,
    scoreType=cv2.ORB_HARRIS_SCORE,
    patchSize=31,
    fastThreshold=20
)


# ORB descriptors use Hamming distance
_BF = cv2.BFMatcher(
    cv2.NORM_HAMMING,
    crossCheck=False
)


# =========================================================
# IMAGE LOADING
# =========================================================

def _load(path, max_dim=1000):
    """
    Load an image from disk.

    Large images are resized so that the verification
    process remains reasonably fast.
    """

    img = cv2.imread(path)

    if img is None:
        raise ValueError(
            f"Could not read image: {path}"
        )

    h, w = img.shape[:2]

    largest_dimension = max(h, w)

    if largest_dimension > max_dim:

        scale = max_dim / largest_dimension

        img = cv2.resize(
            img,
            (
                int(w * scale),
                int(h * scale)
            ),
            interpolation=cv2.INTER_AREA
        )

    return img


# =========================================================
# FEATURE DETECTION
# =========================================================

def _detect_features(img):
    """
    Detect ORB keypoints and descriptors.
    """

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # Improve contrast slightly
    gray = cv2.equalizeHist(gray)

    keypoints, descriptors = _ORB.detectAndCompute(
        gray,
        None
    )

    return keypoints, descriptors


# =========================================================
# IMPORTANT VISUAL REGIONS
# =========================================================

def _important_regions(
    img,
    grid=4,
    top_n=6
):
    """
    Divide the image into a grid.

    Cells with more ORB keypoints are treated as
    important visual regions.
    """

    h, w = img.shape[:2]

    gh = max(
        1,
        h // grid
    )

    gw = max(
        1,
        w // grid
    )

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    gray = cv2.equalizeHist(
        gray
    )

    keypoints, _ = _ORB.detectAndCompute(
        gray,
        None
    )

    cell_scores = {}

    for kp in keypoints or []:

        x, y = kp.pt

        cx = int(x // gw)
        cy = int(y // gh)

        cx = min(
            cx,
            grid - 1
        )

        cy = min(
            cy,
            grid - 1
        )

        cell = (
            cx,
            cy
        )

        cell_scores[cell] = (
            cell_scores.get(
                cell,
                0
            ) + 1
        )

    ranked = sorted(
        cell_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    ranked = ranked[:top_n]

    regions = []

    for (cx, cy), _score in ranked:

        x0 = cx * gw
        y0 = cy * gh

        x1 = min(
            x0 + gw,
            w
        )

        y1 = min(
            y0 + gh,
            h
        )

        regions.append(
            (
                x0,
                y0,
                x1,
                y1
            )
        )

    # If no features were found,
    # use the entire image.
    if not regions:

        regions = [
            (
                0,
                0,
                w,
                h
            )
        ]

    return regions


# =========================================================
# MATCH DESCRIPTORS
# =========================================================

def _good_matches(
    descriptors_a,
    descriptors_b
):
    """
    Match ORB descriptors using Lowe's ratio test.
    """

    if (
        descriptors_a is None
        or descriptors_b is None
    ):
        return []

    if (
        len(descriptors_a) < 2
        or len(descriptors_b) < 2
    ):
        return []

    try:

        matches = _BF.knnMatch(
            descriptors_a,
            descriptors_b,
            k=2
        )

    except cv2.error:

        return []

    good = []

    for pair in matches:

        if len(pair) != 2:
            continue

        m, n = pair

        if m.distance < RATIO_TEST * n.distance:

            good.append(m)

    return good


# =========================================================
# GEOMETRIC VERIFICATION
# =========================================================

def _geometric_verification(
    keypoints_a,
    keypoints_b,
    good_matches
):
    """
    Use RANSAC homography to check whether matched
    points have a consistent geometric relationship.

    This is important because simple feature matching
    alone can produce false matches.
    """

    if len(good_matches) < MIN_GOOD_MATCHES:

        return 0, 0.0

    points_a = np.float32(
        [
            keypoints_a[m.queryIdx].pt
            for m in good_matches
        ]
    ).reshape(
        -1,
        1,
        2
    )

    points_b = np.float32(
        [
            keypoints_b[m.trainIdx].pt
            for m in good_matches
        ]
    ).reshape(
        -1,
        1,
        2
    )

    try:

        homography, mask = cv2.findHomography(
            points_a,
            points_b,
            cv2.RANSAC,
            5.0
        )

    except cv2.error:

        return 0, 0.0

    if (
        homography is None
        or mask is None
    ):

        return 0, 0.0

    mask = mask.ravel()

    inliers = int(
        np.sum(mask)
    )

    inlier_ratio = (
        inliers /
        max(
            1,
            len(good_matches)
        )
    )

    return (
        inliers,
        inlier_ratio
    )


# =========================================================
# GLOBAL IMAGE SIMILARITY
# =========================================================

def _global_similarity(
    img_a,
    img_b
):
    """
    Compare the entire original and captured images.

    Returns:
        score
        good matches
        RANSAC inliers
        inlier ratio
    """

    keypoints_a, descriptors_a = _detect_features(
        img_a
    )

    keypoints_b, descriptors_b = _detect_features(
        img_b
    )

    if (
        descriptors_a is None
        or descriptors_b is None
    ):

        return (
            0.0,
            0,
            0,
            0.0
        )

    good = _good_matches(
        descriptors_a,
        descriptors_b
    )

    good_count = len(good)

    if good_count < MIN_GOOD_MATCHES:

        return (
            0.0,
            good_count,
            0,
            0.0
        )

    inliers, inlier_ratio = _geometric_verification(
        keypoints_a,
        keypoints_b,
        good
    )

    # -----------------------------------------------------
    # Feature match score
    # -----------------------------------------------------

    # More good matches means greater similarity.
    # The value is capped at 100.

    match_score = min(
        100.0,
        (
            good_count /
            max(
                MIN_GOOD_MATCHES,
                30
            )
        ) * 100
    )

    # -----------------------------------------------------
    # Geometric score
    # -----------------------------------------------------

    geometric_score = (
        inlier_ratio * 100
    )

    # -----------------------------------------------------
    # Final global score
    # -----------------------------------------------------

    score = (
        0.35 * match_score
        +
        0.65 * geometric_score
    )

    return (
        min(
            100.0,
            score
        ),
        good_count,
        inliers,
        inlier_ratio
    )


# =========================================================
# REGION SIMILARITY
# =========================================================

def _region_similarity(
    img_a,
    img_b,
    box
):
    """
    Compare one important region.

    Geometric verification is also applied to the region.
    """

    x0, y0, x1, y1 = box

    crop_a = img_a[
        y0:y1,
        x0:x1
    ]

    if crop_a.size == 0:

        return 0.0

    # Resize captured image to original image size
    img_b_resized = cv2.resize(
        img_b,
        (
            img_a.shape[1],
            img_a.shape[0]
        ),
        interpolation=cv2.INTER_AREA
    )

    crop_b = img_b_resized[
        y0:y1,
        x0:x1
    ]

    if crop_b.size == 0:

        return 0.0

    kp_a, des_a = _detect_features(
        crop_a
    )

    kp_b, des_b = _detect_features(
        crop_b
    )

    if (
        des_a is None
        or des_b is None
    ):

        return 0.0

    good = _good_matches(
        des_a,
        des_b
    )

    if len(good) < MIN_GOOD_MATCHES:

        return 0.0

    inliers, inlier_ratio = _geometric_verification(
        kp_a,
        kp_b,
        good
    )

    if inliers < MIN_INLIERS:

        return 0.0

    match_score = min(
        100.0,
        (
            len(good) /
            max(
                MIN_GOOD_MATCHES,
                20
            )
        ) * 100
    )

    geometric_score = (
        inlier_ratio * 100
    )

    score = (
        0.30 * match_score
        +
        0.70 * geometric_score
    )

    return min(
        100.0,
        score
    )


# =========================================================
# MAIN VERIFICATION FUNCTION
# =========================================================

def compare_images(
    original_path,
    captured_path
):
    """
    Main Authentix image verification function.
    """

    # -----------------------------------------------------
    # 1. Load images
    # -----------------------------------------------------

    img_a = _load(
        original_path
    )

    img_b = _load(
        captured_path
    )

    # -----------------------------------------------------
    # 2. Global comparison
    # -----------------------------------------------------

    (
        global_score,
        good_matches,
        inliers,
        inlier_ratio
    ) = _global_similarity(
        img_a,
        img_b
    )

    # -----------------------------------------------------
    # 3. Important region detection
    # -----------------------------------------------------

    regions = _important_regions(
        img_a,
        grid=4,
        top_n=6
    )

    # -----------------------------------------------------
    # 4. Region comparison
    # -----------------------------------------------------

    region_scores = []

    for region in regions:

        score = _region_similarity(
            img_a,
            img_b,
            region
        )

        region_scores.append(
            score
        )

    if region_scores:

        region_avg = float(
            np.mean(
                region_scores
            )
        )

    else:

        region_avg = 0.0

    # -----------------------------------------------------
    # 5. Combine global + region scores
    # -----------------------------------------------------

    if (
        good_matches < MIN_GOOD_MATCHES
        or inliers < MIN_INLIERS
    ):

        # Not enough reliable evidence
        final_score = 0.0

    else:

        final_score = (
            0.60 * global_score
            +
            0.40 * region_avg
        )

    final_score = round(
        max(
            0.0,
            min(
                100.0,
                final_score
            )
        ),
        2
    )

    # -----------------------------------------------------
    # 6. Determine verdict
    # -----------------------------------------------------

    if (
        final_score >= AUTHENTIC_THRESHOLD
        and inliers >= MIN_INLIERS
        and inlier_ratio >= 0.35
    ):

        verdict = "AUTHENTIC"

    elif final_score >= SUSPICIOUS_THRESHOLD:

        verdict = "SUSPICIOUS"

    else:

        verdict = "COUNTERFEIT"

    # -----------------------------------------------------
    # 7. Return result
    # -----------------------------------------------------

    return {
        "similarity": final_score,
        "verdict": verdict,
        "regions_analyzed": len(regions),

        # We are using ORB + RANSAC,
        # not a deep neural network.
        "deep_features_used": False,

        # Extra information useful for debugging
        "good_matches": good_matches,
        "geometric_inliers": inliers,
        "inlier_ratio": round(
            inlier_ratio * 100,
            2
        )
    }