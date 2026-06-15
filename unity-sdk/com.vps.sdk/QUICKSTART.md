# Unity SDK Quickstart — VPS Spatial Platform

This guide walks you from a blank Unity project to your first live localization response using the VPS SDK.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Unity 2022.3 LTS or later | 2023.x also supported |
| Universal Render Pipeline (URP) | Built-in RP also works, but URP is recommended |
| AR Foundation (if using device camera) | Optional: SDK accepts any `Texture2D` source |
| Android or iOS build target | Both platforms supported |
| Camera permissions granted | See platform notes below |
| VPS backend endpoint + API key | Provided at pilot setup |

**Camera permissions:**
- **Android:** add `CAMERA` permission to `AndroidManifest.xml` or via Unity Player Settings → Android → Permissions.
- **iOS:** set `NSCameraUsageDescription` in `Info.plist`.

---

## Installation

The SDK ships as a local Unity package. Copy it into your project:

```bash
# From your project root
cp -r /path/to/com.vps.sdk ./Packages/com.vps.sdk
```

Then open Unity → **Window → Package Manager → + → Add package from disk…** → select `Packages/com.vps.sdk/package.json`.

> **Tip:** You can also add the following entry to `Packages/manifest.json` directly:
> ```json
> "com.vps.sdk": "file:../Packages/com.vps.sdk"
> ```

---

## Inspector Setup

1. Create an empty `GameObject` in your scene (e.g. **VPSController**).
2. Add the `VPSClient` component: **Add Component → VPS → VPSClient**.
3. Fill in the Inspector fields:

| Field | Example Value | Description |
|---|---|---|
| **Base Url** | `https://api.yourvps.io` | Your VPS backend base URL (no trailing slash). |
| **Api Key** | `sk-abc123...` | X-API-Key value from your pilot setup. Leave blank if auth is disabled. |
| **Scene Id** | `kl-central-b1-floor1` | The scene ID created during map capture. |
| **Request Timeout Seconds** | `30` | HTTP request timeout in seconds. |

---

## Subscribing to Events

The `VPSClient` exposes two C# events:

```csharp
public event Action<LocalizationResponse> OnLocalizationSuccess;
public event Action<string> OnLocalizationFailed;
```

Subscribe to them in `Awake` or `Start`:

```csharp
using VPS.SDK;
using UnityEngine;

public class MyLocalizationHandler : MonoBehaviour
{
    [SerializeField] private VPSClient vpsClient;

    private void Awake()
    {
        vpsClient.OnLocalizationSuccess += HandleSuccess;
        vpsClient.OnLocalizationFailed  += HandleFailure;
    }

    private void OnDestroy()
    {
        vpsClient.OnLocalizationSuccess -= HandleSuccess;
        vpsClient.OnLocalizationFailed  -= HandleFailure;
    }

    private void HandleSuccess(LocalizationResponse response)
    {
        Debug.Log($"Localized! pos={response.x:F3},{response.y:F3},{response.z:F3}  " +
                  $"confidence={response.confidence:F2}  inliers={response.inliers}");
    }

    private void HandleFailure(string error)
    {
        Debug.LogWarning($"Localization failed: {error}");
    }
}
```

---

## Calling CaptureAndLocalize

### Option A — Pass a Texture2D directly

```csharp
// Anywhere in your MonoBehaviour (e.g. on button press or on AR frame update):
Texture2D frame = CaptureCurrentCameraFrame(); // your helper
vpsClient.Localize(frame);
```

### Option B — Pass raw JPEG bytes

```csharp
byte[] jpegBytes = ...; // e.g. from ARCameraBackground
vpsClient.Localize(jpegBytes);
```

The SDK encodes `Texture2D` to JPEG at quality 80 before sending. If you already have JPEG bytes, use the `byte[]` overload to avoid double-encoding.

---

## Understanding the LocalizationResponse

```csharp
[Serializable]
public class LocalizationResponse
{
    public float x;          // Camera X position in COLMAP scene space (metres)
    public float y;          // Camera Y position in COLMAP scene space (metres)
    public float z;          // Camera Z position in COLMAP scene space (metres)
    public float qx;         // Rotation quaternion X
    public float qy;         // Rotation quaternion Y
    public float qz;         // Rotation quaternion Z
    public float qw;         // Rotation quaternion W
    public float confidence; // [0.0 – 1.0] matching confidence
    public int   inliers;    // Number of matched feature inliers
}
```

### Confidence Interpretation

| Condition | Status | Meaning |
|---|---|---|
| `inliers > 30` AND `confidence > 0.50` | **Locked** | High-confidence fix; update your AR pose. |
| `inliers >= 15` AND `confidence >= 0.30` | **Weak** | Usable but uncertain; show a "searching…" indicator. |
| Otherwise | **Failed** | Discard; keep previous pose. |

---

## Applying the Pose in Your Scene

VPS returns position in **COLMAP scene space** — a coordinate system defined during map building. This is not the same as Unity world space.

**Recommended pattern:** place a `VPSSceneAnchor` GameObject in your scene at a known reference point, then apply the localized pose relative to it.

```csharp
private void HandleSuccess(LocalizationResponse r)
{
    // Interpret the response
    float confidence = r.confidence;
    int   inliers    = r.inliers;

    bool isLocked = inliers > 30 && confidence > 0.50f;
    bool isWeak   = inliers >= 15 && confidence >= 0.30f;

    if (!isLocked && !isWeak)
    {
        Debug.Log("Localization confidence too low — skipping pose update.");
        return;
    }

    // Apply pose relative to scene anchor
    Vector3    scenePos = new Vector3(r.x, r.y, r.z);
    Quaternion sceneRot = new Quaternion(r.qx, r.qy, r.qz, r.qw);

    // sceneAnchor is a GameObject at your map's origin in Unity world space
    transform.position = sceneAnchor.transform.TransformPoint(scenePos);
    transform.rotation = sceneAnchor.transform.rotation * sceneRot;

    if (isWeak)
        ShowWeakLockIndicator();
    else
        HideWeakLockIndicator();
}
```

> **Note:** The scene anchor's world position and rotation must match the physical origin used during site scanning. Misalignment here is the most common cause of AR drift.

---

## Full Minimal MonoBehaviour Example

```csharp
using System.Collections;
using UnityEngine;
using VPS.SDK;

/// <summary>
/// Minimal VPS localization loop: captures every 3 seconds and updates transform.
/// </summary>
public class VPSLocalizationLoop : MonoBehaviour
{
    [Header("VPS")]
    [SerializeField] private VPSClient  vpsClient;
    [SerializeField] private Transform  sceneAnchor;   // empty GO at map origin in Unity world
    [SerializeField] private Camera     captureCamera; // the camera to capture from

    [Header("Timing")]
    [SerializeField] private float localizationIntervalSeconds = 3f;

    private void Awake()
    {
        vpsClient.OnLocalizationSuccess += ApplyPose;
        vpsClient.OnLocalizationFailed  += (err) => Debug.LogWarning($"VPS: {err}");
    }

    private IEnumerator Start()
    {
        while (true)
        {
            yield return new WaitForSeconds(localizationIntervalSeconds);
            RequestLocalization();
        }
    }

    private void RequestLocalization()
    {
        // Render current camera view into a temporary texture
        RenderTexture rt = new RenderTexture(640, 360, 24);
        captureCamera.targetTexture = rt;
        captureCamera.Render();

        RenderTexture.active = rt;
        Texture2D frame = new Texture2D(640, 360, TextureFormat.RGB24, false);
        frame.ReadPixels(new Rect(0, 0, 640, 360), 0, 0);
        frame.Apply();

        captureCamera.targetTexture = null;
        RenderTexture.active = null;
        Destroy(rt);

        vpsClient.Localize(frame);
        Destroy(frame);
    }

    private void ApplyPose(LocalizationResponse r)
    {
        bool locked = r.inliers > 30 && r.confidence > 0.50f;
        bool weak   = r.inliers >= 15 && r.confidence >= 0.30f;

        if (!locked && !weak) return;

        Vector3    pos = new Vector3(r.x, r.y, r.z);
        Quaternion rot = new Quaternion(r.qx, r.qy, r.qz, r.qw);

        transform.position = sceneAnchor.TransformPoint(pos);
        transform.rotation = sceneAnchor.rotation * rot;
    }

    private void OnDestroy()
    {
        vpsClient.OnLocalizationSuccess -= ApplyPose;
    }
}
```

---

## Error Handling Patterns

| Error string | Likely cause | Action |
|---|---|---|
| `Scene ID is not set.` | `SceneId` field blank in Inspector | Set it in Inspector or via `vpsClient.SceneId = "..."` |
| `VPS API base URL is not set.` | `BaseUrl` field blank | Set backend URL |
| `Localization request failed: ...` | Network error, timeout, or 401 Unauthorized | Check `baseUrl`, `apiKey`, and network connectivity |
| `Parse Error` | Backend returned unexpected JSON | Check backend logs; may indicate feature extraction failure |
| No event fired at all | Coroutine not started | Ensure `VPSClient` MonoBehaviour is active; check console for exceptions |

---

## Platform-Specific Notes

- **Android:** target API 23+ for runtime permission prompts. Test on a physical device — Unity Editor localizes against a static image.
- **iOS:** The camera texture is available via `ARCameraBackground` or `WebCamTexture`. Ensure Metal rendering is enabled.
- **Unity Editor (PC/Mac):** Use a static `Texture2D` asset for testing without a physical device camera.
