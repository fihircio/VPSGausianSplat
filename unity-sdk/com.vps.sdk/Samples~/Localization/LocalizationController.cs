using UnityEngine;
using UnityEngine.UI;
using VPS.SDK;

public class LocalizationController : MonoBehaviour
{
    [Header("VPS")]
    [SerializeField] private VPSClient vpsClient;
    [SerializeField] private MapSpace mapSpace;
    [SerializeField] private Camera arCamera;

    [Header("Capture")]
    [SerializeField] private int captureWidth = 640;
    [SerializeField] private int captureHeight = 360;
    [SerializeField] private float captureInterval = 3f;

    [Header("HUD")]
    [SerializeField] private Text statusText;
    [SerializeField] private Text confidenceText;
    [SerializeField] private Text inliersText;
    [SerializeField] private GameObject lockIndicator;
    [SerializeField] private GameObject weakLockIndicator;

    [Header("AR Content")]
    [SerializeField] private GameObject arContentRoot;

    private WebCamTexture _webcam;
    private bool _isCapturing;

    private void Awake()
    {
        if (arCamera == null) arCamera = Camera.main;
        if (mapSpace == null) mapSpace = FindObjectOfType<MapSpace>();
        if (vpsClient == null) vpsClient = FindObjectOfType<VPSClient>();

        vpsClient.OnLocalizationSuccess += OnLocalized;
        vpsClient.OnLocalizationFailed += OnFailed;
    }

    private void Start()
    {
        StartWebCam();
        if (arContentRoot != null)
            arContentRoot.SetActive(false);
    }

    private void StartWebCam()
    {
        if (WebCamTexture.devices.Length == 0)
        {
            SetStatus("No camera found");
            return;
        }

        _webcam = new WebCamTexture(captureWidth, captureHeight);
        _webcam.Play();
        _isCapturing = true;
        SetStatus("Camera started. Localizing...");
        InvokeRepeating(nameof(CaptureAndLocalize), 1f, captureInterval);
    }

    private void CaptureAndLocalize()
    {
        if (!_isCapturing || _webcam == null || !_webcam.isPlaying) return;

        Texture2D frame = new Texture2D(_webcam.width, _webcam.height, TextureFormat.RGB24, false);
        frame.SetPixels(_webcam.GetPixels());
        frame.Apply();

        vpsClient.Localize(frame);
        Destroy(frame, 0.5f);
    }

    private void OnLocalized(LocalizationResponse response)
    {
        bool locked = response.inliers > 30 && response.confidence > 0.50f;
        bool weak = response.inliers >= 15 && response.confidence >= 0.30f;

        if (locked)
        {
            SetStatus("Localized (Locked)");
            if (lockIndicator != null) lockIndicator.SetActive(true);
            if (weakLockIndicator != null) weakLockIndicator.SetActive(false);
            if (arContentRoot != null) arContentRoot.SetActive(true);
        }
        else if (weak)
        {
            SetStatus("Localized (Weak)");
            if (lockIndicator != null) lockIndicator.SetActive(false);
            if (weakLockIndicator != null) weakLockIndicator.SetActive(true);
        }
        else
        {
            SetStatus("Low confidence - retrying...");
            if (lockIndicator != null) lockIndicator.SetActive(false);
            if (weakLockIndicator != null) weakLockIndicator.SetActive(false);
        }

        if (confidenceText != null)
            confidenceText.text = $"Conf: {response.confidence:P1}";
        if (inliersText != null)
            inliersText.text = $"Inliers: {response.inliers}";
    }

    private void OnFailed(string error)
    {
        SetStatus($"Failed: {error}");
        if (lockIndicator != null) lockIndicator.SetActive(false);
        if (weakLockIndicator != null) weakLockIndicator.SetActive(false);
    }

    private void SetStatus(string msg)
    {
        if (statusText != null)
            statusText.text = msg;
        Debug.Log($"[LocalizationSample] {msg}");
    }

    private void OnDestroy()
    {
        if (_webcam != null && _webcam.isPlaying)
            _webcam.Stop();

        CancelInvoke();
        if (vpsClient != null)
        {
            vpsClient.OnLocalizationSuccess -= OnLocalized;
            vpsClient.OnLocalizationFailed -= OnFailed;
        }
    }
}
