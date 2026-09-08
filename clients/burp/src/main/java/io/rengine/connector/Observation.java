package io.rengine.connector;

import java.util.List;

/** One request and its response, as the ingest endpoint expects it. */
record Observation(
        String url,
        String method,
        Integer statusCode,
        String contentType,
        Integer contentLength,
        String title,
        boolean authenticated,
        String sourceTool,
        List<String> bodyParams) {

    String toJson() {
        Json json = new Json().object()
                .field("url", url)
                .field("method", method)
                .field("status_code", statusCode)
                .field("content_type", contentType)
                .field("content_length", contentLength)
                .field("title", title)
                .field("authenticated", authenticated)
                .field("source_tool", sourceTool);
        if (!bodyParams.isEmpty()) {
            json.raw("body_params", Json.array(bodyParams));
        }
        return json.end().toString();
    }
}
