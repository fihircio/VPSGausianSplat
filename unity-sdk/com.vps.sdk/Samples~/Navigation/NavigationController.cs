using UnityEngine;
using UnityEngine.AI;
using UnityEngine.UI;
using VPS.SDK;

public class NavigationController : MonoBehaviour
{
    [Header("VPS")]
    [SerializeField] private VPSClient vpsClient;
    [SerializeField] private MapSpace mapSpace;
    [SerializeField] private Camera arCamera;

    [Header("Navigation")]
    [SerializeField] private Transform targetMarker;
    [SerializeField] private NavMeshAgent agent;
    [SerializeField] private float arrivalDistance = 1.5f;

    [Header("WebSocket Sync")]
    [SerializeField] private WebSocketClient wsClient;
    [SerializeField] private bool syncViaWebSocket;

    [Header("UI")]
    [SerializeField] private Text statusText;
    [SerializeField] private Text distanceText;
    [SerializeField] private GameObject pathLinePrefab;
    [SerializeField] private LineRenderer pathLine;

    [Header("Capture")]
    [SerializeField] private float captureInterval = 2f;

    private WebCamTexture _webcam;
    private Vector3 _currentVpsPosition;
    private bool _hasVpsFix;
    private Vector3? _targetPosition;

    private void Awake()
    {
        if (arCamera == null) arCamera = Camera.main;
        if (mapSpace == null) mapSpace = FindObjectOfType<MapSpace>();
        if (vpsClient == null) vpsClient = FindObjectOfType<VPSClient>();
        if (agent == null) agent = GetComponent<NavMeshAgent>();

        vpsClient.OnLocalizationSuccess += OnLocalized;
        vpsClient.OnLocalizationFailed += OnFailed;

        if (wsClient != null)
        {
            wsClient.OnAgentPoseReceived += OnRemotePose;
            wsClient.OnConnected += () => SetStatus("WebSocket connected");
        }
    }

    private void Start()
    {
        StartWebCam();
        InvokeRepeating(nameof(CaptureAndLocalize), 1f, captureInterval);

        if (wsClient != null && syncViaWebSocket)
            wsClient.Connect();

        if (pathLine != null)
            pathLine.positionCount = 0;
    }

    private void StartWebCam()
    {
        if (WebCamTexture.devices.Length == 0)
        {
            SetStatus("No camera");
            return;
        }
        _webcam = new WebCamTexture(640, 360);
        _webcam.Play();
    }

    private void Update()
    {
        if (!_hasVpsFix) return;

        if (_targetPosition.HasValue)
        {
            float dist = Vector3.Distance(_currentVpsPosition, _targetPosition.Value);
            if (distanceText != null)
                distanceText.text = $"Distance: {dist:F1}m";

            if (agent != null && agent.isActiveAndEnabled)
            {
                agent.SetDestination(_targetPosition.Value);
                if (dist <= arrivalDistance)
                {
                    SetStatus("Arrived at target");
                    _targetPosition = null;
                }
            }
        }

        UpdatePathLine();
        SyncPoseToServer();
    }

    public void SetTarget(Vector3 worldPosition)
    {
        _targetPosition = worldPosition;
        SetStatus("Navigating to target...");

        if (targetMarker != null)
            targetMarker.position = worldPosition;
    }

    public void ClearTarget()
    {
        _targetPosition = null;
        SetStatus("Target cleared");
        if (agent != null) agent.ResetPath();
        if (pathLine != null) pathLine.positionCount = 0;
    }

    private void CaptureAndLocalize()
    {
        if (_webcam == null || !_webcam.isPlaying) return;

        Texture2D frame = new Texture2D(_webcam.width, _webcam.height, TextureFormat.RGB24, false);
        frame.SetPixels(_webcam.GetPixels());
        frame.Apply();

        vpsClient.Localize(frame);
        Destroy(frame, 0.5f);
    }

    private void OnLocalized(LocalizationResponse response)
    {
        bool usable = response.inliers >= 15 && response.confidence >= 0.30f;
        if (!usable)
        {
            SetStatus("VPS fix too weak for navigation");
            return;
        }

        _currentVpsPosition = response.GetUnityPosition();
        _hasVpsFix = true;
        SetStatus($"VPS fix: conf={response.confidence:P1}, inliers={response.inliers}");

        if (_targetPosition.HasValue && agent != null)
        {
            agent.SetDestination(_targetPosition.Value);
        }
    }

    private void OnFailed(string error)
    {
        SetStatus($"VPS: {error}");
    }

    private void OnRemotePose(AgentPoseUpdate pose)
    {
        Vector3 pos = CoordinateConverter.ArrayToVector3(pose.position);
        Quaternion rot = CoordinateConverter.ArrayToQuaternion(pose.rotation);
        Debug.Log($"Remote agent '{pose.name}' at {pos}");
    }

    private void SyncPoseToServer()
    {
        if (wsClient == null || !syncViaWebSocket || !_hasVpsFix) return;

        AgentPoseUpdate update = new AgentPoseUpdate
        {
            type = "pose_update",
            agent_id = wsClient.AgentId,
            name = "UnityNaviAgent",
            role = "navigator",
            position = new float[] { _currentVpsPosition.x, _currentVpsPosition.y, _currentVpsPosition.z },
            rotation = new float[] { 0, 0, 0, 1 }
        };
        wsClient.SendPoseUpdate(update);
    }

    private void UpdatePathLine()
    {
        if (pathLine == null || !_hasVpsFix || !_targetPosition.HasValue) return;

        Vector3[] corners = agent != null ? agent.path.corners : null;
        if (corners != null && corners.Length > 0)
        {
            pathLine.positionCount = corners.Length;
            pathLine.SetPositions(corners);
        }
    }

    private void SetStatus(string msg)
    {
        if (statusText != null) statusText.text = msg;
        Debug.Log($"[NavigationSample] {msg}");
    }

    private void OnDestroy()
    {
        if (_webcam != null && _webcam.isPlaying) _webcam.Stop();
        CancelInvoke();

        if (vpsClient != null)
        {
            vpsClient.OnLocalizationSuccess -= OnLocalized;
            vpsClient.OnLocalizationFailed -= OnFailed;
        }
        if (wsClient != null)
            wsClient.OnAgentPoseReceived -= OnRemotePose;
    }
}
