using System;
using System.Collections;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace VPS.SDK
{
    public class WebSocketClient : MonoBehaviour
    {
        [SerializeField] private string wsUrl = "wss://api.yourvps.io/ws/navigatus";
        [SerializeField] private string agentId = "unity-agent";
        [SerializeField] private float reconnectDelaySeconds = 5f;
        [SerializeField] private int maxReconnectAttempts = 5;

        public event Action<AgentPoseUpdate> OnAgentPoseReceived;
        public event Action OnConnected;
        public event Action<string> OnDisconnected;
        public event Action<string> OnError;

        public string AgentId { get => agentId; set => agentId = value; }
        public bool IsConnected => _ws != null && _ws.State == WebSocketState.Open;

        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;
        private int _reconnectCount;

        public void Connect()
        {
            if (_ws != null && _ws.State == WebSocketState.Open) return;
            StartCoroutine(ConnectRoutine());
        }

        public void Disconnect()
        {
            _cts?.Cancel();
            if (_ws != null)
            {
                try
                {
                    _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client disconnect", CancellationToken.None).ConfigureAwait(false);
                }
                catch { }
                _ws.Dispose();
                _ws = null;
            }
        }

        public void SendPoseUpdate(AgentPoseUpdate update)
        {
            if (!IsConnected) return;
            string json = JsonUtility.ToJson(update);
            byte[] data = Encoding.UTF8.GetBytes(json);
            try
            {
                _ws.SendAsync(new ArraySegment<byte>(data), WebSocketMessageType.Text, true, _cts.Token).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                OnError?.Invoke($"Send error: {ex.Message}");
            }
        }

        private IEnumerator ConnectRoutine()
        {
            Disconnect();
            _cts = new CancellationTokenSource();
            _ws = new ClientWebSocket();

            string uri = $"{wsUrl.TrimEnd('/')}/{agentId}";
            Task connectTask = _ws.ConnectAsync(new Uri(uri), _cts.Token);

            yield return new WaitUntil(() => connectTask.IsCompleted);

            if (connectTask.IsFaulted || connectTask.IsCanceled)
            {
                OnError?.Invoke($"Connection failed: {connectTask.Exception?.Message ?? "cancelled"}");
                _ws.Dispose();
                _ws = null;
                TryReconnect();
                yield break;
            }

            _reconnectCount = 0;
            OnConnected?.Invoke();
            StartCoroutine(ReceiveLoop());
        }

        private IEnumerator ReceiveLoop()
        {
            byte[] buffer = new byte[4096];
            StringBuilder messageBuilder = new StringBuilder();

            while (_ws != null && _ws.State == WebSocketState.Open && _cts != null && !_cts.IsCancellationRequested)
            {
                messageBuilder.Clear();
                ArraySegment<byte> segment = new ArraySegment<byte>(buffer);

                Task<WebSocketReceiveResult> receiveTask = _ws.ReceiveAsync(segment, _cts.Token);

                yield return new WaitUntil(() => receiveTask.IsCompleted);

                if (receiveTask.IsFaulted || receiveTask.IsCanceled) break;

                WebSocketReceiveResult result = receiveTask.Result;
                messageBuilder.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));

                while (!result.EndOfMessage)
                {
                    receiveTask = _ws.ReceiveAsync(segment, _cts.Token);
                    yield return new WaitUntil(() => receiveTask.IsCompleted);
                    if (receiveTask.IsFaulted || receiveTask.IsCanceled) break;
                    result = receiveTask.Result;
                    messageBuilder.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                }

                if (result.MessageType == WebSocketMessageType.Close) break;

                try
                {
                    var pose = JsonUtility.FromJson<AgentPoseUpdate>(messageBuilder.ToString());
                    OnAgentPoseReceived?.Invoke(pose);
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"Failed to parse pose update: {ex.Message}");
                }
            }

            OnDisconnected?.Invoke("WebSocket connection closed.");
            TryReconnect();
        }

        private void TryReconnect()
        {
            if (_reconnectCount >= maxReconnectAttempts)
            {
                OnError?.Invoke("Max reconnect attempts reached.");
                return;
            }

            _reconnectCount++;
            StartCoroutine(ConnectRoutine());
        }

        private void OnDestroy()
        {
            Disconnect();
        }
    }
}
