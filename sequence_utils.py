# sequence_utils.py
import random as R

# --- Sequence Generation (from Step 1) ---

def generate_dna_sequence(id: int, region: str, age: int, dna_seed: str) -> str:
    """
    Generates a DNA sequence based on ID, region, age, and a seed string.
    (This is the function adapted from the original func.py)
    """
    R.seed(f"{id}+{region}+{age}")

    def core():
        x = 1
        for _ in range(100_000):
            x = (x * 987654321) % 123456789
        return x

    Q = {
        "apac": ["agtc", "agct", "actg", "atgc", "actg", "agtc"],
        "na": ["gtac", "gcat", "gcta"],
        "latam": ["cgta", "ctga", "catg"],
        "emea": ["aagt", "aatg", "aagc"],
    }
    valid_motifs = {q for v in Q.values() for q in v}

    F = lambda S: list(
        {
            S[i : i + 4]
            for i in range(0, len(S) - 3, 4) # Non-overlapping step 4
            if S[i : i + 4] in valid_motifs
        }
    )

    L, T, C = [], 0, 1010101010

    while T < C:
        core()
        M = F(dna_seed)
        if not M:
            return "x" # Indicates invalid seed (no motifs found)

        try:
            Z = R.choice(M) # Should not fail if M is not empty
            N = R.randint(10**3, 10**5)
        except IndexError:
             # Should theoretically not happen if 'if not M' check is working
             print(f"Warning: R.choice failed unexpectedly with M={M}. Returning 'x'.")
             return "x"

        W = Z * N
        L.append(W)
        T += len(W)
        # Safety break (optional, if C is excessively large)
        if T > (C + 10**6):
            print("Warning: Sequence generation hit safety break length.")
            break

    final_sequence = "".join(L)
    return final_sequence[:C]


# --- Sequence Comparison (Step 6 Implementation) ---

def get_kmers(sequence: str, k: int = 4) -> set[str]:
    """
    Extracts all unique, overlapping k-mers (substrings of length k) from a sequence.

    Args:
        sequence: The DNA sequence string.
        k: The length of the k-mer (default: 4).

    Returns:
        A set of unique k-mers found in the sequence.
    """
    if not isinstance(sequence, str) or len(sequence) < k or k <= 0:
        return set() # Return empty set if sequence is too short, not string, or k is invalid

    kmers = set()
    # Iterate through the sequence to extract overlapping k-mers
    for i in range(len(sequence) - k + 1):
        kmer = sequence[i:i+k]
        kmers.add(kmer)
    return kmers

def compare_sequences(seq1: str, seq2: str, k: int = 4) -> float:
    """
    Compares two DNA sequences based on the Jaccard Index of their k-mers.
    Similarity = |Intersection(Kmers1, Kmers2)| / |Union(Kmers1, Kmers2)|

    Args:
        seq1: The first DNA sequence string.
        seq2: The second DNA sequence string.
        k: The length of k-mers to use for comparison (default: 4).

    Returns:
        A similarity score between 0.0 (no common k-mers) and 1.0 (identical sets of k-mers).
    """
    # Handle cases where input might not be strings (though API should pass strings)
    if not isinstance(seq1, str) or not isinstance(seq2, str):
        return 0.0

    # Handle identical sequences quickly
    if seq1 == seq2:
        return 1.0

    # Get the sets of k-mers for both sequences
    kmers1 = get_kmers(seq1, k)
    kmers2 = get_kmers(seq2, k)

    # Calculate the size of the intersection and union
    intersection_size = len(kmers1.intersection(kmers2))
    union_size = len(kmers1.union(kmers2))

    # Calculate Jaccard Index
    if union_size == 0:
        # This happens if both sequences are too short to contain any k-mers (e.g., < k length)
        # If they weren't identical (checked above), similarity is 0
        return 0.0
    else:
        similarity = intersection_size / union_size
        return similarity