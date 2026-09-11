#!/bin/zsh
FP=/private/tmp/claude-501/-Users-eturner-Projects-trace/d95239a6-d0bf-4437-a43b-60504b786a6e/scratchpad/fp
cd $FP/model-provenance-kit
log=$FP/cisco-out/driver.log
echo "$(date +%T) download deep signals" >> $log
.venv/bin/provenancekit download-deepsignals-fingerprint >> $log 2>&1
for m in HuggingFaceH4/zephyr-7b-beta dphn/dolphin-2.9-llama3-8b Qwen/Qwen2.5-7B-Instruct teknium/OpenHermes-2.5-Mistral-7B; do
  echo "$(date +%T) scan $m" >> $log
  .venv/bin/provenancekit scan $m --json --top-k 5 --threshold 0.0 > $FP/cisco-out/scan-${m//\//--}.json 2>> $log
  echo "$(date +%T) scan $m exit $?" >> $log
done
echo "$(date +%T) compare dolphin vs Mistral-7B-v0.1" >> $log
.venv/bin/provenancekit compare dphn/dolphin-2.9-llama3-8b mistralai/Mistral-7B-v0.1 --json > $FP/cisco-out/compare-dolphin--Mistral-7B-v0.1.json 2>> $log
echo "$(date +%T) done exit $?" >> $log
