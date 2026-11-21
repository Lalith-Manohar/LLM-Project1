import sys
import shutil
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

base_dir = Path(".").resolve()
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    print(f"=== TESTING ISOLATED FRESH CLONE ENVIRONMENT: {temp_path} ===")
    
    # Mirror structure
    ml_dir = temp_path / "backend" / "ml"
    raw_dir = ml_dir / "data" / "raw"
    proc_dir = ml_dir / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)

    # Copy ONLY what git tracks in a fresh clone
    shutil.copy2(base_dir / "backend" / "ml" / "data" / "raw" / "online_retail_II.csv", raw_dir / "online_retail_II.csv")
    shutil.copy2(base_dir / "backend" / "ml" / "data" / "processed" / "daily_product_demand.csv", proc_dir / "daily_product_demand.csv")
    shutil.copytree(base_dir / "backend" / "ml" / "models", ml_dir / "models")
    shutil.copytree(base_dir / "backend" / "ml" / "models_task12", ml_dir / "models_task12")

    clean_sales = proc_dir / "clean_gross_sales.csv"
    pit_cache = proc_dir / "pit_sku_price_history.json"
    assert not clean_sales.exists(), "clean_gross_sales.csv must NOT exist initially"
    assert not pit_cache.exists(), "pit_sku_price_history.json must NOT exist initially"
    print("Initial fresh clone state verified: derived CSV and cache are absent.")

    # Initialize PointInTimePriceService pointing to isolated proc_dir
    from ml.src.point_in_time_price import PointInTimePriceService
    pit_svc = PointInTimePriceService(data_dir=proc_dir)
    pit_svc.load_index()
    
    assert clean_sales.exists(), "clean_gross_sales.csv should be auto-generated!"
    assert pit_cache.exists(), "pit_sku_price_history.json should be auto-generated!"
    print(f"Auto-initialization SUCCESS: clean_gross_sales ({clean_sales.stat().st_size:,} bytes), cache ({pit_cache.stat().st_size:,} bytes).")

    # Test price resolution
    p_85123a = pit_svc.get_price("85123A", "2011-12-09")
    print(f"Resolved price for 85123A: {p_85123a}")
    assert p_85123a > 0.0

    print("=== FRESH CLONE ISOLATED REPRODUCIBILITY TEST PASSED! ===")
