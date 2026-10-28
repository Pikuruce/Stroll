# 変数定義
ENTRY_POINT = main.py
OUTPUT_PARENT = build
BUILD_DIR = $(OUTPUT_PARENT)/main.dist

.PHONY: run build clean

# 1. ゲームを通常起動する (uv run)
run:
	uv run $(ENTRY_POINT)

# 2. Nuitkaでbuild/フォルダー内にビルドする
build:
	uv run nuitka \
		--standalone \
		--follow-imports \
		--output-dir=$(OUTPUT_PARENT) \
		--include-data-dir=assets=assets \
		--include-data-files=config.yaml=config.yaml \
		$(ENTRY_POINT)

# 3. ビルド成果物やキャッシュを削除してクリーンにする
clean:
	@if [ -d "$(OUTPUT_PARENT)" ]; then rm -rf $(OUTPUT_PARENT); echo "Removed $(OUTPUT_PARENT) folder"; fi
	@if [ -d "main.build" ]; then rm -rf main.build; echo "Removed main.build"; fi

