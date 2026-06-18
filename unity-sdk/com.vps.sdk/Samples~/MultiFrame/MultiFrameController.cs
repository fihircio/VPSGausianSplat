using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using VPS.SDK;

public class MultiFrameController : MonoBehaviour
{
    [Header("VPS")]
    [SerializeField] private VPSClient vpsClient;
    [SerializeField] private MapSpace mapSpace;
    [SerializeField] private Camera arCamera;

    [Header("Capture Settings")]
    [SerializeField][Range(2, 6)] private int frameCount = 4;
    [SerializeField] private float frameInterval = 0.5f;
    [SerializeField] private int captureWidth = 640;
    [SerializeField] private int captureHeight = 360;

    [Header("UI")]
    [SerializeField] private Text statusText;
    [SerializeField] private Text confidenceText;
    [SerializeField] private Text inliersText;
    [SerializeField] private Text framesUsedText;
    [SerializeField] private GameObject lockIndicator;
    [SerializeField] private GameObject[] confidenceBars;
    [SerializeField] private Text[] frameLabelTexts;
    [SerializeField] private Button captureButton;
    [SerializeField] private Image[] frameThumbnails;

    [Header("AR Content")]
    [SerializeField] private GameObject arContentRoot;

    private WebCamTexture _webcam;
    private bool _isCapturing;

    private void Awake()
    {
        if (arCamera == null) arCamera = Camera.main;
        if (mapSpace == null) mapSpace = FindObjectOfType<MapSpace>();
        if (vpsClient == null) vpsClient = FindObjectOfType<VPSClient>();

        vpsClient.OnMultiFrameLocalizationSuccess += OnMultiLocalized;
        vpsClient.OnLocalizationFailed += OnFailed;

        if (captureButton != null)
            captureButton.onClick.AddListener(StartMultiFrameCapture);
    }

    private void Start()
    {
        StartWebCam();
        ResetConfidenceBars();
        if (arContentRoot != null) arContentRoot.SetActive(false);
    }

    private void StartWebCam()
    {
        if (WebCamTexture.devices.Length == 0)
        {
            SetStatus("No camera");
            return;
        }
        _webcam = new WebCamTexture(captureWidth, captureHeight);
        _webcam.Play();
        _isCapturing = true;
        SetStatus("Tap capture to begin multi-frame localization");
    }

    public void StartMultiFrameCapture()
    {
        if (!_isCapturing || _webcam == null || !_webcam.isPlaying) return;
        StartCoroutine(MultiFrameCaptureRoutine());
    }

    private IEnumerator MultiFrameCaptureRoutine()
    {
        SetStatus($"Capturing {frameCount} frames...");
        if (captureButton != null) captureButton.interactable = false;

        ResetConfidenceBars();
        List<Texture2D> frames = new List<Texture2D>();

        for (int i = 0; i < frameCount; i++)
        {
            Texture2D frame = new Texture2D(_webcam.width, _webcam.height, TextureFormat.RGB24, false);
            frame.SetPixels(_webcam.GetPixels());
            frame.Apply();
            frames.Add(frame);

            if (frameThumbnails != null && i < frameThumbnails.Length && frameThumbnails[i] != null)
                frameThumbnails[i].sprite = Sprite.Create(frame, new Rect(0, 0, frame.width, frame.height), Vector2.zero);

            if (frameLabelTexts != null && i < frameLabelTexts.Length && frameLabelTexts[i] != null)
                frameLabelTexts[i].text = $"Frame {i + 1}";

            SetStatus($"Captured frame {i + 1}/{frameCount}");

            if (i < frameCount - 1)
                yield return new WaitForSeconds(frameInterval);
        }

        SetStatus("Localizing with multi-frame...");
        vpsClient.LocalizeMulti(frames.ToArray());

        foreach (Texture2D frame in frames)
            Destroy(frame, 1f);
    }

    private void OnMultiLocalized(MultiFrameLocalizationResponse response)
    {
        bool locked = response.inliers > 30 && response.confidence > 0.50f;
        bool weak = response.inliers >= 15 && response.confidence >= 0.30f;

        if (locked)
        {
            SetStatus("Localized (Locked)");
            if (lockIndicator != null) lockIndicator.SetActive(true);
            if (arContentRoot != null) arContentRoot.SetActive(true);
        }
        else if (weak)
        {
            SetStatus("Localized (Weak)");
            if (lockIndicator != null) lockIndicator.SetActive(false);
        }
        else
        {
            SetStatus("Low confidence - try again");
            if (lockIndicator != null) lockIndicator.SetActive(false);
        }

        if (confidenceText != null)
            confidenceText.text = $"Confidence: {response.confidence:P1}";
        if (inliersText != null)
            inliersText.text = $"Inliers: {response.inliers}";
        if (framesUsedText != null)
            framesUsedText.text = $"Frames Used: {response.frames_used} / {frameCount}";

        UpdateConfidenceBars(response.frame_confidences);
        ResetCaptureButton();
    }

    private void OnFailed(string error)
    {
        SetStatus($"Failed: {error}");
        if (lockIndicator != null) lockIndicator.SetActive(false);
        ResetCaptureButton();
    }

    private void UpdateConfidenceBars(float[] confidences)
    {
        if (confidenceBars == null) return;

        for (int i = 0; i < confidenceBars.Length; i++)
        {
            if (confidenceBars[i] == null) continue;
            Image barImage = confidenceBars[i].GetComponent<Image>();
            if (barImage == null) continue;

            float conf = (confidences != null && i < confidences.Length) ? confidences[i] : 0f;
            barImage.fillAmount = Mathf.Clamp01(conf);

            if (conf >= 0.5f)
                barImage.color = Color.green;
            else if (conf >= 0.3f)
                barImage.color = Color.yellow;
            else
                barImage.color = Color.red;
        }
    }

    private void ResetConfidenceBars()
    {
        if (confidenceBars == null) return;
        foreach (var bar in confidenceBars)
        {
            if (bar == null) continue;
            Image img = bar.GetComponent<Image>();
            if (img != null) img.fillAmount = 0f;
        }
    }

    private void ResetCaptureButton()
    {
        if (captureButton != null)
            captureButton.interactable = true;
    }

    private void SetStatus(string msg)
    {
        if (statusText != null) statusText.text = msg;
        Debug.Log($"[MultiFrameSample] {msg}");
    }

    private void OnDestroy()
    {
        if (_webcam != null && _webcam.isPlaying) _webcam.Stop();
        StopAllCoroutines();

        if (vpsClient != null)
        {
            vpsClient.OnMultiFrameLocalizationSuccess -= OnMultiLocalized;
            vpsClient.OnLocalizationFailed -= OnFailed;
        }
    }
}
