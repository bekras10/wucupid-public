# Matching Algorithm

This document explains the WUCupid matching system at a high level.

The core idea: separate **eligibility** from **ranking**.

- Eligibility is determined by hard compatibility constraints.
- Ranking is determined by personality similarity and soft preferences.
- Final matches are selected using mutual top-k.

## Inputs

Each submitted user had two broad sets of data.

## 1. Hard/profile fields

These fields were used for compatibility and filtering:

- gender
- sexual orientation / interest
- academic year
- religion
- political view
- preferred academic years
- preferred religions
- preferred political views

## 2. Survey responses

Users answered Likert-style personality/preference questions.

Typical answer values:

```text
Strongly disagree = -2
Disagree          = -1
Neutral           =  0
Agree             =  1
Strongly agree    =  2
```

Some questions were reverse-scored before vector construction.

## Step 1: Build user vectors

Each user was represented as a numeric vector.

### Personality vector

Survey answers became a vector of numeric values.

Reverse-scored questions were multiplied by `-1`, so that higher/lower values had consistent directionality.

### Soft-filter vector

Profile values were one-hot encoded:

- academic year
- religion
- political view

These dimensions were weighted differently from the personality survey.

Historical weights:

```python
WEIGHT_RELIGION = 3.0
WEIGHT_POLITICS = 2.0
WEIGHT_YEAR = 1.5
WEIGHT_PERSONALITY = 1.0
```

The personality weight was dynamically scaled based on the number of survey questions so changes in survey length did not completely distort the weighting balance.

### Normalization

The final vector was L2-normalized so cosine similarity could be computed efficiently as a dot product.

## Step 2: Hard compatibility mask

Before ranking, the system built a compatibility matrix from gender and interest/orientation fields.

A pair was eligible only if both users could date each other.

Example:

```text
A is interested in women
B is female
=> A can date B

B is interested in everyone
A's gender is included
=> B can date A

Both directions true
=> pair is eligible
```

Incompatible pairs were assigned a score of `-1`, which removed them from consideration.

This matters because soft preferences should not override basic eligibility.

## Step 3: Base similarity

For eligible users, the system computed vector similarity:

```text
similarity = normalized_user_vector_A dot normalized_user_vector_B
```

Because vectors were normalized, this is equivalent to cosine similarity.

Higher scores meant the users were more similar based on the weighted feature representation.

## Step 4: Apply soft preference bonuses/penalties

Soft preferences adjusted scores but did not override hard compatibility.

Preference categories:

- preferred academic years
- preferred religions
- preferred political views

The system applied directional bonuses/penalties.

Example:

```text
A prefers Juniors
B is a Junior
=> A's score toward B gets a bonus

A prefers Juniors
B is a Senior
=> A's score toward B gets a small penalty
```

Because preferences can be asymmetric, the score from A to B and B to A could differ. Final pair score used an average of the two directions.

## Step 5: Mutual top-k selection

Each user ranked eligible candidates by score.

The system then selected pairs only when the match was mutual:

```text
A is in B's top k
AND
B is in A's top k
=> create match
```

The production value was generally:

```python
k = 3
```

This reduced chain-effect problems where a user could be assigned to someone who ranked them poorly.

## Step 6: Deduplication and persistence

Pairs were sorted consistently by email before insertion. This prevented duplicate versions of the same match.

Example:

```text
(a@example.edu, b@example.edu)
```

rather than sometimes storing:

```text
(b@example.edu, a@example.edu)
```

The database also enforced uniqueness per cycle:

```text
cycle_id + user1_email + user2_email
```

## Optional filler matches

The code supported optional filler matches through an environment flag.

Purpose:

- reduce the number of users with zero matches
- provide coverage in sparse cohorts
- pair unmatched users with compatible users when no mutual top-k match existed

Filler match scores were intentionally low, roughly in the `0.10–0.25` range.

Because filler status was not stored as an explicit boolean, historical filler counts are best treated as estimated unless logs are available.

## Why this design

## Hard constraints first

Gender/orientation compatibility is not a "preference bonus." It determines whether a pair is even valid.

## Soft preferences second

Academic year, religion, and politics can matter, but they should not fully dominate personality or hard compatibility.

## Mutual top-k

Pure greedy matching can create bad outcomes because one highly ranked user can distort many pairings.

Mutual top-k favors pairs where both users rank each other relatively highly.

## Vectorized implementation

The system computed matrices using NumPy so matching could scale better than naive nested scoring logic.

At WUCupid's campus-scale dataset size, this was more than sufficient.

## Known limitations

- Matching quality depends heavily on survey design.
- Sparse subgroups can still produce unmatched users.
- Soft preference weights were manually selected rather than learned from outcome data.
- Filler matches were operationally useful but analytically less clean.
- No explicit post-match feedback loop was incorporated.
- The algorithm optimized compatibility scores, not confirmed relationship outcomes.

## Future improvements

If the project continued, useful next steps would include:

- storing `is_filler` on matches
- tracking match impressions/clicks in aggregate
- adding explicit user feedback after match release
- tuning weights from observed outcomes
- running offline simulations before each cycle
- adding fairness/coverage reports by cohort
- adding stronger privacy-preserving analytics exports
