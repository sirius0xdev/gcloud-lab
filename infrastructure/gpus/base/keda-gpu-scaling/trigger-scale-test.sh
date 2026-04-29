# Test script to trigger KEDA scale-up for rtx6000 vLLM
# Run this from a machine with kubectl access to the cluster

kubectl run -n customer1 --rm -it scale-test --image=curlimages/curl --restart=Never -- sh -c '
  echo "Sending request to trigger scaling..."
  curl -s -X POST http://rtx6000-brain-service:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"Hello"}],"max_tokens":20,"stream":false}' | head -c 200
  echo -e "\n\nRequest sent. Watch scaling now."
' 
