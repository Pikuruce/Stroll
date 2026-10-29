# 変数定義
ENTRY_POINT = main.py
OUTPUT_PARENT = build

.PHONY: run build clean

# 通常起動
run:
	uv run $(ENTRY_POINT)

# 単一のexeファイルを生成
build:
	uv run nuitka \
		--onefile \
		--follow-imports \
		--output-dir=$(OUTPUT_PARENT) \
		--output-filename=Stroll.exe \
		--windows-icon-from-ico=icon.ico \
		--include-data-dir=assets=assets \
		--include-data-files=config.yaml=config.yaml \
		$(ENTRY_POINT)

# ビルド成果物を削除
clean:
	@if [ -d "$(OUTPUT_PARENT)" ]; then rm -rf "$(OUTPUT_PARENT)"; echo "Removed $(OUTPUT_PARENT) folder"; fi
	@if [ -d "main.build" ]; then rm -rf "main.build"; echo "Removed main.build"; fi
	@if [ -d "main.onefile-build" ]; then rm -rf "main.onefile-build"; echo "Removed main.onefile-build"; fi