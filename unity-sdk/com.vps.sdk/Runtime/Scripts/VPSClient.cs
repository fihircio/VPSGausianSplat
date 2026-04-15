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
        [SerializeField] private string baseUrl = "http://localhost:8000";
        [SerializeField] private string sceneId;

        public event Action<LocalizationResponse> OnLocalizationSuccess;
        public event Action<string> OnLocalizationFailed;

        public string BaseUrl { get => baseUrl; set => baseUrl = value; }
        public string SceneId { get => sceneId; set => sceneId = value; }

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

            string url = $"{baseUrl}/vps/localize";

            List<IMultipartFormSection> formData = new List<IMultipartFormSection>();
            formData.Add(new MultipartFormDataSection("scene_id", sceneId));
            formData.Add(new MultipartFormFileSection("query_image", jpegData, "query.jpg", "image/jpeg"));

            using (UnityWebRequest www = UnityWebRequest.Post(url, formData))
            {
                yield return www.SendWebRequest();

                if (www.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"VPS Localization Failed: {www.error}\n{www.downloadHandler.text}");
                    OnLocalizationFailed?.Invoke(www.error);
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
