using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System;

namespace VPS.SDK
{
    public class VPSClient : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [SerializeField] private string baseUrl = "";
        [SerializeField] private string apiKey = "";
        [SerializeField] private string sceneId;
        [SerializeField] private int requestTimeoutSeconds = 30;

        public event Action<LocalizationResponse> OnLocalizationSuccess;
        public event Action<string> OnLocalizationFailed;

        public string BaseUrl { get => baseUrl; set => baseUrl = value; }
        public string ApiKey { get => apiKey; set => apiKey = value; }
        public string SceneId { get => sceneId; set => sceneId = value; }
        public int RequestTimeoutSeconds { get => requestTimeoutSeconds; set => requestTimeoutSeconds = value; }

        /// <summary>
        /// Captures a frame from a Texture2D and sends it for localization.
        /// </summary>
        public void Localize(Texture2D texture)
        {
            byte[] jpegData = texture.EncodeToJPG(80);
            StartCoroutine(PostLocalizationRequest(jpegData));
        }

        /// <summary>
        /// Sends raw JPEG data for localization.
        /// </summary>
        public void Localize(byte[] jpegData)
        {
            StartCoroutine(PostLocalizationRequest(jpegData));
        }

        private IEnumerator PostLocalizationRequest(byte[] jpegData)
        {
            if (string.IsNullOrEmpty(sceneId))
            {
                OnLocalizationFailed?.Invoke("Scene ID is not set.");
                yield break;
            }

            string normalizedBaseUrl = baseUrl?.TrimEnd('/');
            if (string.IsNullOrEmpty(normalizedBaseUrl))
            {
                OnLocalizationFailed?.Invoke("VPS API base URL is not set.");
                yield break;
            }

            string url = $"{normalizedBaseUrl}/vps/localize";

            List<IMultipartFormSection> formData = new List<IMultipartFormSection>();
            formData.Add(new MultipartFormDataSection("scene_id", sceneId));
            formData.Add(new MultipartFormFileSection("query_image", jpegData, "query.jpg", "image/jpeg"));

            using (UnityWebRequest www = UnityWebRequest.Post(url, formData))
            {
                www.timeout = Math.Max(0, requestTimeoutSeconds);
                if (!string.IsNullOrEmpty(apiKey))
                {
                    www.SetRequestHeader("X-API-Key", apiKey);
                }

                yield return www.SendWebRequest();

                if (www.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"VPS Localization Failed: {www.error}\n{www.downloadHandler.text}");
                    OnLocalizationFailed?.Invoke($"Localization request failed: {www.error}");
                }
                else
                {
                    try
                    {
                        var response = JsonUtility.FromJson<LocalizationResponse>(www.downloadHandler.text);
                        OnLocalizationSuccess?.Invoke(response);
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"Failed to parse VPS response: {ex.Message}");
                        OnLocalizationFailed?.Invoke("Parse Error");
                    }
                }
            }
        }
    }
}
