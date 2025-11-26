"""
Benchmark utility for WhisperTux
Evaluates models for optimal WER vs inference time trade-off
"""

import json
import time
import random
import tempfile
import wave
import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple
import numpy as np

try:
    from .whisper_manager import WhisperManager
    from .config_manager import ConfigManager
    from .audio_capture import AudioCapture
except ImportError:
    from whisper_manager import WhisperManager
    from config_manager import ConfigManager
    from audio_capture import AudioCapture


# Text samples for benchmark reading - approximately 20-30 seconds each when read aloud
# Each sample is designed to test different phonetic patterns and vocabulary
BENCHMARK_SAMPLES = [
    {
        "id": "sample_01",
        "text": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet. "
                "Speech recognition systems need to handle a wide variety of phonetic patterns to work effectively. "
                "Modern neural networks have revolutionized how we approach this problem, "
                "enabling real-time transcription with remarkable accuracy.",
        "category": "pangram_technical",
        "estimated_seconds": 25
    },
    {
        "id": "sample_02",
        "text": "Yesterday I went to the grocery store to buy some vegetables. "
                "The carrots were on sale, so I grabbed a few bags. "
                "Then I stopped by the bakery section for some fresh bread. "
                "The cashier was friendly and helped me find my loyalty card. "
                "Shopping on weekday mornings is much quieter than weekends.",
        "category": "everyday_narrative",
        "estimated_seconds": 28
    },
    {
        "id": "sample_03",
        "text": "Machine learning models require substantial computational resources for training. "
                "Graphics processing units accelerate matrix operations significantly. "
                "The transformer architecture has become dominant in natural language processing. "
                "Attention mechanisms allow models to focus on relevant input features. "
                "Fine-tuning pre-trained models reduces the data requirements substantially.",
        "category": "technical_ml",
        "estimated_seconds": 30
    },
    {
        "id": "sample_04",
        "text": "Please remember to schedule the meeting for next Tuesday at three o'clock. "
                "We should invite the marketing team and the product managers. "
                "The agenda will cover quarterly results and upcoming launches. "
                "Someone needs to book the large conference room on the second floor. "
                "Make sure to send the calendar invite with the video call link.",
        "category": "business_speech",
        "estimated_seconds": 26
    },
    {
        "id": "sample_05",
        "text": "The weather forecast predicts scattered showers throughout the afternoon. "
                "Temperatures will range between sixty-five and seventy-two degrees Fahrenheit. "
                "A cold front is moving in from the northwest bringing cooler air. "
                "Winds will be light and variable, mostly from the south. "
                "Tomorrow should be partly cloudy with a chance of sunshine.",
        "category": "weather_numbers",
        "estimated_seconds": 27
    },
    {
        "id": "sample_06",
        "text": "Open source software development relies on community contributions. "
                "Version control systems like Git enable collaborative coding workflows. "
                "Pull requests allow maintainers to review changes before merging. "
                "Documentation is essential for helping new contributors get started. "
                "Testing frameworks ensure code quality and prevent regressions.",
        "category": "technical_software",
        "estimated_seconds": 26
    },
    {
        "id": "sample_07",
        "text": "My phone number is five five five, one two three, four five six seven. "
                "The appointment is scheduled for January fifteenth, twenty twenty-five. "
                "The total comes to forty-seven dollars and ninety-three cents. "
                "Room three hundred and twelve is located on the third floor. "
                "Please arrive at least fifteen minutes before your scheduled time.",
        "category": "numbers_dates",
        "estimated_seconds": 28
    },
    {
        "id": "sample_08",
        "text": "Cooking a proper risotto requires patience and constant attention. "
                "Start by toasting the arborio rice in butter until translucent. "
                "Add warm stock gradually while stirring continuously. "
                "The dish should reach a creamy consistency after about eighteen minutes. "
                "Finish with parmesan cheese and a knob of cold butter.",
        "category": "cooking_instructions",
        "estimated_seconds": 25
    },
    {
        "id": "sample_09",
        "text": "The human brain contains approximately eighty-six billion neurons. "
                "Synaptic connections form complex networks enabling thought and memory. "
                "Neuroscience research has advanced significantly in recent decades. "
                "Brain plasticity allows neural pathways to reorganize throughout life. "
                "Understanding consciousness remains one of science's greatest challenges.",
        "category": "science_biology",
        "estimated_seconds": 27
    },
    {
        "id": "sample_10",
        "text": "Would you like to hear about today's specials? We have grilled salmon "
                "served with roasted asparagus and lemon butter sauce. "
                "There's also a vegetarian option featuring stuffed bell peppers. "
                "For dessert, the chef recommends the chocolate lava cake. "
                "Can I get you something to drink while you look at the menu?",
        "category": "restaurant_dialogue",
        "estimated_seconds": 26
    },
]


@dataclass
class BenchmarkResult:
    """Result from benchmarking a single model on a single sample"""
    model_name: str
    sample_id: str
    reference_text: str
    transcribed_text: str
    word_error_rate: float
    inference_time_seconds: float
    audio_duration_seconds: float
    real_time_factor: float  # inference_time / audio_duration (< 1 means faster than real-time)
    timestamp: str


@dataclass
class ModelSummary:
    """Aggregated results for a model across all samples"""
    model_name: str
    average_wer: float
    std_wer: float
    average_inference_time: float
    std_inference_time: float
    average_rtf: float  # Real-time factor
    samples_tested: int
    efficiency_score: float  # Combined metric for recommendation
    recommendation_rank: int


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) using Levenshtein distance at word level.

    WER = (Substitutions + Insertions + Deletions) / Total Words in Reference

    Args:
        reference: Ground truth text
        hypothesis: Transcribed text to evaluate

    Returns:
        WER as a float between 0.0 and potentially > 1.0 (if many insertions)
    """
    # Normalize texts: lowercase, strip, split into words
    ref_words = reference.lower().strip().split()
    hyp_words = hypothesis.lower().strip().split()

    if len(ref_words) == 0:
        return 1.0 if len(hyp_words) > 0 else 0.0

    # Dynamic programming for edit distance
    m, n = len(ref_words), len(hyp_words)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for i in range(m + 1):
        dp[i][0] = i  # Deletions
    for j in range(n + 1):
        dp[0][j] = j  # Insertions

    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                dp[i][j] = dp[i-1][j-1]  # No operation needed
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],      # Deletion
                    dp[i][j-1],      # Insertion
                    dp[i-1][j-1]     # Substitution
                )

    edit_distance = dp[m][n]
    wer = edit_distance / len(ref_words)

    return wer


def calculate_efficiency_score(wer: float, inference_time: float, audio_duration: float) -> float:
    """
    Calculate an efficiency score that balances accuracy and speed.

    For real-time voice typing, we want:
    1. Low WER (high accuracy) - weighted more heavily
    2. Low inference time relative to audio duration (fast enough for real-time)

    The formula considers:
    - Accuracy term: (1 - WER) represents transcription quality (0 to 1)
    - Speed term: Penalizes if inference takes longer than audio (real-time factor > 1)
    - For voice typing, anything under 0.5x real-time is excellent

    Score formula:
    efficiency = (1 - WER)^2 / (1 + max(0, RTF - 0.3))

    This:
    - Squares accuracy to heavily penalize errors
    - Only penalizes speed if RTF > 0.3 (30% of real-time is the "free" threshold)
    - Returns values roughly between 0 and 1, higher is better

    Args:
        wer: Word error rate (0.0 to 1.0+)
        inference_time: Time taken for transcription in seconds
        audio_duration: Duration of the audio in seconds

    Returns:
        Efficiency score (higher is better)
    """
    # Clamp WER to reasonable bounds
    wer_clamped = min(max(wer, 0.0), 1.0)

    # Calculate real-time factor
    rtf = inference_time / audio_duration if audio_duration > 0 else float('inf')

    # Accuracy term - squared to penalize errors more heavily
    accuracy_term = (1 - wer_clamped) ** 2

    # Speed penalty - only kicks in above 0.3x real-time
    # This means models that process in under 30% of audio time get no penalty
    speed_threshold = 0.3
    speed_penalty = 1 + max(0, rtf - speed_threshold)

    efficiency = accuracy_term / speed_penalty

    return efficiency


class WhisperBenchmark:
    """Benchmark utility for comparing Whisper models"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the benchmark utility.

        Args:
            config_manager: Optional ConfigManager instance, creates new one if not provided
        """
        self.config = config_manager or ConfigManager()
        self.whisper = WhisperManager(self.config)
        self.audio_capture = None  # Initialize on demand

        # Results storage
        self.results_dir = self.config.config_dir / "benchmark_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Current session results
        self.current_results: List[BenchmarkResult] = []

    def initialize(self) -> bool:
        """Initialize the benchmark system"""
        if not self.whisper.initialize():
            print("ERROR: Failed to initialize Whisper manager")
            return False
        return True

    def get_available_models(self) -> List[str]:
        """Get list of available models for benchmarking"""
        return self.whisper.get_available_models()

    def get_benchmark_samples(self, count: int = 10, shuffle: bool = True) -> List[Dict]:
        """
        Get text samples for benchmark reading.

        Args:
            count: Number of samples to return (max 10)
            shuffle: Whether to randomize the order

        Returns:
            List of sample dictionaries with 'id', 'text', 'category', 'estimated_seconds'
        """
        samples = BENCHMARK_SAMPLES.copy()

        if shuffle:
            random.shuffle(samples)

        return samples[:min(count, len(samples))]

    def record_sample(self, sample_id: str, duration_hint: float = 30.0) -> Tuple[Optional[np.ndarray], float]:
        """
        Record audio for a benchmark sample.

        Args:
            sample_id: ID of the sample being recorded
            duration_hint: Expected duration in seconds (for display purposes)

        Returns:
            Tuple of (audio_data as numpy array, actual duration in seconds)
        """
        if self.audio_capture is None:
            self.audio_capture = AudioCapture()
            if not self.audio_capture.initialize():
                print("ERROR: Failed to initialize audio capture")
                return None, 0.0

        print(f"\n--- Recording Sample: {sample_id} ---")
        print(f"Expected duration: ~{duration_hint:.0f} seconds")
        print("Press ENTER to start recording...")
        input()

        print("Recording... Press ENTER when finished.")
        self.audio_capture.start_recording()
        input()
        self.audio_capture.stop_recording()

        audio_data = self.audio_capture.get_audio()
        if audio_data is None or len(audio_data) == 0:
            print("ERROR: No audio captured")
            return None, 0.0

        # Calculate duration (16kHz sample rate)
        duration = len(audio_data) / 16000.0
        print(f"Recorded {duration:.1f} seconds of audio")

        return audio_data, duration

    def save_audio_to_file(self, audio_data: np.ndarray, filepath: Path, sample_rate: int = 16000):
        """Save audio data to a WAV file"""
        # Convert float32 to int16
        if audio_data.dtype == np.float32:
            audio_int16 = (audio_data * 32767).astype(np.int16)
        else:
            audio_int16 = audio_data.astype(np.int16)

        with wave.open(str(filepath), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

    def load_audio_from_file(self, filepath: Path) -> Tuple[Optional[np.ndarray], float]:
        """Load audio data from a WAV file"""
        try:
            with wave.open(str(filepath), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                audio_bytes = wav_file.readframes(n_frames)

                # Convert to numpy array
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float = audio_int16.astype(np.float32) / 32767.0

                duration = n_frames / sample_rate
                return audio_float, duration

        except Exception as e:
            print(f"ERROR: Failed to load audio from {filepath}: {e}")
            return None, 0.0

    def benchmark_single(
        self,
        model_name: str,
        audio_data: np.ndarray,
        reference_text: str,
        sample_id: str,
        audio_duration: float
    ) -> Optional[BenchmarkResult]:
        """
        Benchmark a single model on a single audio sample.

        Args:
            model_name: Name of the model to test
            audio_data: Audio data as numpy array
            reference_text: Ground truth text
            sample_id: ID of the sample
            audio_duration: Duration of audio in seconds

        Returns:
            BenchmarkResult or None if failed
        """
        # Switch to the model
        if not self.whisper.set_model(model_name):
            print(f"ERROR: Failed to switch to model: {model_name}")
            return None

        # Time the transcription
        start_time = time.perf_counter()
        transcribed_text = self.whisper.transcribe_audio(audio_data)
        end_time = time.perf_counter()

        inference_time = end_time - start_time

        # Calculate WER
        wer = calculate_wer(reference_text, transcribed_text)

        # Calculate real-time factor
        rtf = inference_time / audio_duration if audio_duration > 0 else float('inf')

        result = BenchmarkResult(
            model_name=model_name,
            sample_id=sample_id,
            reference_text=reference_text,
            transcribed_text=transcribed_text,
            word_error_rate=wer,
            inference_time_seconds=inference_time,
            audio_duration_seconds=audio_duration,
            real_time_factor=rtf,
            timestamp=datetime.now().isoformat()
        )

        return result

    def run_full_benchmark(
        self,
        models: Optional[List[str]] = None,
        num_samples: int = 10,
        save_audio: bool = True
    ) -> Dict[str, ModelSummary]:
        """
        Run a full benchmark session.

        This will:
        1. Present text samples to read
        2. Record user speaking each sample
        3. Test each model on each recording
        4. Calculate WER and timing for each
        5. Generate recommendations

        Args:
            models: List of model names to test (None = all available)
            num_samples: Number of samples to test
            save_audio: Whether to save recorded audio for future use

        Returns:
            Dictionary mapping model names to ModelSummary objects
        """
        if models is None:
            models = self.get_available_models()

        if not models:
            print("ERROR: No models available for benchmarking")
            return {}

        print("\n" + "=" * 60)
        print("WhisperTux Model Benchmark")
        print("=" * 60)
        print(f"\nModels to test: {len(models)}")
        for m in models:
            print(f"  - {m}")
        print(f"\nSamples to record: {num_samples}")
        print("\nFor each sample, you will:")
        print("  1. See the text to read")
        print("  2. Press ENTER to start recording")
        print("  3. Read the text aloud")
        print("  4. Press ENTER when finished")
        print("\nThe same recording will be tested against all models.")
        print("\n" + "=" * 60)

        input("\nPress ENTER to begin...")

        # Get samples
        samples = self.get_benchmark_samples(num_samples)

        # Session directory for audio files
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.results_dir / f"session_{session_id}"
        if save_audio:
            session_dir.mkdir(parents=True, exist_ok=True)

        # Collect recordings
        recordings: List[Dict] = []

        for i, sample in enumerate(samples, 1):
            print(f"\n{'=' * 60}")
            print(f"Sample {i} of {len(samples)}: {sample['category']}")
            print("=" * 60)
            print(f"\nREAD THIS TEXT:\n")
            print(f"  {sample['text']}")
            print(f"\n(Estimated reading time: ~{sample['estimated_seconds']} seconds)")

            audio_data, duration = self.record_sample(sample['id'], sample['estimated_seconds'])

            if audio_data is None:
                print("Skipping this sample due to recording error")
                continue

            # Save audio if requested
            audio_path = None
            if save_audio:
                audio_path = session_dir / f"{sample['id']}.wav"
                self.save_audio_to_file(audio_data, audio_path)
                print(f"Audio saved to: {audio_path}")

            recordings.append({
                'sample': sample,
                'audio_data': audio_data,
                'duration': duration,
                'audio_path': audio_path
            })

        if not recordings:
            print("ERROR: No recordings captured")
            return {}

        # Now test each model on each recording
        print("\n" + "=" * 60)
        print("Running transcriptions...")
        print("=" * 60)

        all_results: List[BenchmarkResult] = []

        for model in models:
            print(f"\nTesting model: {model}")

            for rec in recordings:
                sample = rec['sample']
                print(f"  - Sample: {sample['id']}...", end=" ", flush=True)

                result = self.benchmark_single(
                    model_name=model,
                    audio_data=rec['audio_data'],
                    reference_text=sample['text'],
                    sample_id=sample['id'],
                    audio_duration=rec['duration']
                )

                if result:
                    all_results.append(result)
                    print(f"WER: {result.word_error_rate:.2%}, Time: {result.inference_time_seconds:.2f}s")
                else:
                    print("FAILED")

        self.current_results = all_results

        # Calculate summaries
        summaries = self._calculate_summaries(all_results)

        # Save results
        self._save_results(session_id, all_results, summaries)

        # Print report
        self._print_report(summaries)

        return summaries

    def _calculate_summaries(self, results: List[BenchmarkResult]) -> Dict[str, ModelSummary]:
        """Calculate summary statistics for each model"""
        # Group results by model
        by_model: Dict[str, List[BenchmarkResult]] = {}
        for r in results:
            if r.model_name not in by_model:
                by_model[r.model_name] = []
            by_model[r.model_name].append(r)

        summaries: Dict[str, ModelSummary] = {}

        for model_name, model_results in by_model.items():
            wers = [r.word_error_rate for r in model_results]
            times = [r.inference_time_seconds for r in model_results]
            rtfs = [r.real_time_factor for r in model_results]
            durations = [r.audio_duration_seconds for r in model_results]

            avg_wer = np.mean(wers)
            avg_time = np.mean(times)
            avg_rtf = np.mean(rtfs)
            avg_duration = np.mean(durations)

            # Calculate efficiency score using averages
            efficiency = calculate_efficiency_score(avg_wer, avg_time, avg_duration)

            summaries[model_name] = ModelSummary(
                model_name=model_name,
                average_wer=avg_wer,
                std_wer=np.std(wers) if len(wers) > 1 else 0.0,
                average_inference_time=avg_time,
                std_inference_time=np.std(times) if len(times) > 1 else 0.0,
                average_rtf=avg_rtf,
                samples_tested=len(model_results),
                efficiency_score=efficiency,
                recommendation_rank=0  # Will be set after sorting
            )

        # Rank by efficiency score
        ranked = sorted(summaries.values(), key=lambda s: s.efficiency_score, reverse=True)
        for i, summary in enumerate(ranked, 1):
            summaries[summary.model_name].recommendation_rank = i

        return summaries

    def _save_results(
        self,
        session_id: str,
        results: List[BenchmarkResult],
        summaries: Dict[str, ModelSummary]
    ):
        """Save benchmark results to JSON"""
        output = {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'results': [asdict(r) for r in results],
            'summaries': {k: asdict(v) for k, v in summaries.items()},
            'recommendation': None
        }

        # Add recommendation
        ranked = sorted(summaries.values(), key=lambda s: s.recommendation_rank)
        if ranked:
            best = ranked[0]
            output['recommendation'] = {
                'model': best.model_name,
                'reason': f"Best efficiency score ({best.efficiency_score:.3f}) with "
                         f"{best.average_wer:.1%} WER and {best.average_rtf:.2f}x real-time factor"
            }

        # Save to file
        output_path = self.results_dir / f"benchmark_{session_id}.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to: {output_path}")

    def _print_report(self, summaries: Dict[str, ModelSummary]):
        """Print a formatted benchmark report"""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)

        # Sort by recommendation rank
        ranked = sorted(summaries.values(), key=lambda s: s.recommendation_rank)

        # Header
        print(f"\n{'Rank':<6} {'Model':<35} {'WER':<10} {'RTF':<10} {'Efficiency':<12}")
        print("-" * 80)

        for s in ranked:
            print(f"{s.recommendation_rank:<6} {s.model_name:<35} "
                  f"{s.average_wer:>7.1%}   {s.average_rtf:>7.2f}x  "
                  f"{s.efficiency_score:>9.3f}")

        print("-" * 80)

        # Legend
        print("\nLegend:")
        print("  WER: Word Error Rate (lower is better)")
        print("  RTF: Real-Time Factor (< 1.0 = faster than real-time, lower is better)")
        print("  Efficiency: Combined score (higher is better)")

        # Recommendation
        if ranked:
            best = ranked[0]
            print("\n" + "=" * 80)
            print("RECOMMENDATION")
            print("=" * 80)
            print(f"\n  Best model for voice typing: {best.model_name}")
            print(f"\n  This model achieves:")
            print(f"    - {best.average_wer:.1%} word error rate")
            print(f"    - {best.average_rtf:.2f}x real-time factor ({best.average_inference_time:.2f}s average)")
            print(f"    - Efficiency score: {best.efficiency_score:.3f}")

            # Explain the trade-off if there's a notable difference
            if len(ranked) > 1:
                most_accurate = min(ranked, key=lambda s: s.average_wer)
                fastest = min(ranked, key=lambda s: s.average_rtf)

                if most_accurate != best:
                    print(f"\n  Note: {most_accurate.model_name} has lower WER ({most_accurate.average_wer:.1%})")
                    print(f"        but is slower ({most_accurate.average_rtf:.2f}x RTF)")

                if fastest != best and fastest != most_accurate:
                    print(f"\n  Note: {fastest.model_name} is fastest ({fastest.average_rtf:.2f}x RTF)")
                    print(f"        but has higher WER ({fastest.average_wer:.1%})")

        print("\n" + "=" * 80)

    def run_from_saved_audio(
        self,
        audio_dir: Path,
        models: Optional[List[str]] = None,
        reference_texts: Optional[Dict[str, str]] = None
    ) -> Dict[str, ModelSummary]:
        """
        Run benchmark using previously recorded audio files.

        Args:
            audio_dir: Directory containing WAV files
            models: List of models to test (None = all available)
            reference_texts: Dict mapping sample_id to reference text (None = use built-in)

        Returns:
            Dictionary mapping model names to ModelSummary objects
        """
        if models is None:
            models = self.get_available_models()

        # Load audio files
        audio_files = list(audio_dir.glob("*.wav"))
        if not audio_files:
            print(f"ERROR: No WAV files found in {audio_dir}")
            return {}

        # Build reference text lookup
        if reference_texts is None:
            reference_texts = {s['id']: s['text'] for s in BENCHMARK_SAMPLES}

        print(f"\nLoaded {len(audio_files)} audio files")
        print(f"Testing {len(models)} models")

        all_results: List[BenchmarkResult] = []

        for model in models:
            print(f"\nTesting model: {model}")

            for audio_path in audio_files:
                sample_id = audio_path.stem

                if sample_id not in reference_texts:
                    print(f"  - {sample_id}: No reference text, skipping")
                    continue

                audio_data, duration = self.load_audio_from_file(audio_path)
                if audio_data is None:
                    continue

                print(f"  - {sample_id}...", end=" ", flush=True)

                result = self.benchmark_single(
                    model_name=model,
                    audio_data=audio_data,
                    reference_text=reference_texts[sample_id],
                    sample_id=sample_id,
                    audio_duration=duration
                )

                if result:
                    all_results.append(result)
                    print(f"WER: {result.word_error_rate:.2%}, Time: {result.inference_time_seconds:.2f}s")
                else:
                    print("FAILED")

        self.current_results = all_results

        # Calculate summaries
        summaries = self._calculate_summaries(all_results)

        # Save results
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_rerun"
        self._save_results(session_id, all_results, summaries)

        # Print report
        self._print_report(summaries)

        return summaries


def main():
    """CLI entry point for benchmark utility"""
    import argparse

    parser = argparse.ArgumentParser(
        description="WhisperTux Model Benchmark - Find the optimal model for your hardware"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Run benchmark command
    run_parser = subparsers.add_parser('run', help='Run a new benchmark session')
    run_parser.add_argument(
        '--models', '-m',
        nargs='+',
        help='Specific models to test (default: all available)'
    )
    run_parser.add_argument(
        '--samples', '-n',
        type=int,
        default=10,
        help='Number of samples to record (default: 10)'
    )
    run_parser.add_argument(
        '--no-save-audio',
        action='store_true',
        help='Do not save recorded audio files'
    )

    # Rerun from saved audio
    rerun_parser = subparsers.add_parser('rerun', help='Rerun benchmark using saved audio')
    rerun_parser.add_argument(
        'audio_dir',
        type=Path,
        help='Directory containing WAV files from previous session'
    )
    rerun_parser.add_argument(
        '--models', '-m',
        nargs='+',
        help='Specific models to test (default: all available)'
    )

    # List available models
    list_parser = subparsers.add_parser('list', help='List available models')

    # Show samples
    samples_parser = subparsers.add_parser('samples', help='Show benchmark text samples')

    args = parser.parse_args()

    if args.command == 'list':
        benchmark = WhisperBenchmark()
        if benchmark.initialize():
            models = benchmark.get_available_models()
            print("\nAvailable models:")
            for m in models:
                print(f"  - {m}")
        return

    if args.command == 'samples':
        print("\nBenchmark text samples:")
        for i, sample in enumerate(BENCHMARK_SAMPLES, 1):
            print(f"\n{i}. [{sample['category']}] (~{sample['estimated_seconds']}s)")
            print(f"   {sample['text'][:80]}...")
        return

    if args.command == 'run':
        benchmark = WhisperBenchmark()
        if not benchmark.initialize():
            print("ERROR: Failed to initialize benchmark")
            return

        benchmark.run_full_benchmark(
            models=args.models,
            num_samples=args.samples,
            save_audio=not args.no_save_audio
        )
        return

    if args.command == 'rerun':
        benchmark = WhisperBenchmark()
        if not benchmark.initialize():
            print("ERROR: Failed to initialize benchmark")
            return

        benchmark.run_from_saved_audio(
            audio_dir=args.audio_dir,
            models=args.models
        )
        return

    # No command specified - show help
    parser.print_help()


if __name__ == '__main__':
    main()
