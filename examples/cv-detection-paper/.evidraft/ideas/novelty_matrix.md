<!-- ILLUSTRATIVE EXAMPLE -- novelty matrix for cv-detection-paper. -->

# Novelty matrix (cv-detection-paper, illustrative)

| Idea                                | Problem                                  | Prior Work                                       | Novelty                                                | Evidence       | Experiment Needed                   | Patent Potential | Risk   |
|-------------------------------------|------------------------------------------|--------------------------------------------------|--------------------------------------------------------|----------------|-------------------------------------|------------------|--------|
| IoU-aware gate on anchor-free head  | Misalignment of cls and reg quality      | smith2024examplekey, chen2023anchorfreebaseline  | Couples cls logits with reg-branch IoU score per loc.  | ev_0018        | Ablate IoU gate (exp_2026_03_02)    | low              | medium |
| Distribution-focal decoding         | Hard-target regression is noisy          | smith2024examplekey                              | 16-bin distribution per side; decoded as expectation.  | ev_0043        | none in this example                | low              | low    |
