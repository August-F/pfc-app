#!/bin/sh
# pre-push hook: main ブランチへのプッシュ前に pytest を実行する
# 使い方: cp docs/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push

while read local_ref local_oid remote_ref remote_oid; do
    case "$remote_ref" in
        refs/heads/main)
            echo "[pre-push] main へのプッシュを検出。pytest を実行します..."

            REPO_ROOT="$(git rev-parse --show-toplevel)"
            cd "$REPO_ROOT/src" || { echo "[pre-push] ERROR: src/ が見つかりません"; exit 1; }

            pytest --tb=short -q
            RESULT=$?

            if [ $RESULT -ne 0 ]; then
                echo ""
                echo "[pre-push] テストが失敗しました。プッシュを中断します。"
                echo "  テストを修正してから再度 git push してください。"
                echo "  スキップする場合: git push --no-verify"
                exit 1
            fi

            echo "[pre-push] テスト通過。プッシュを続行します。"
            ;;
    esac
done

exit 0
