import { LocalizeResponse, MultiFrameLocalizeResponse, Scene, LocalizeOptions, MultiFrameLocalizeOptions } from './types';
export declare class VpsClient {
    private baseUrl;
    private apiKey?;
    constructor(baseUrl: string, apiKey?: string);
    private headers;
    private request;
    getScene(sceneId: string): Promise<Scene>;
    listScenes(): Promise<Scene[]>;
    localize(sceneId: string, image: Blob, options?: LocalizeOptions): Promise<LocalizeResponse>;
    localizeMulti(sceneId: string, images: Blob[], options?: MultiFrameLocalizeOptions): Promise<MultiFrameLocalizeResponse>;
}
