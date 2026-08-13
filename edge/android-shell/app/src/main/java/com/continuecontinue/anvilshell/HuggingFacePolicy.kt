package com.continuecontinue.anvilshell

data class HuggingFaceAsset(
    val repoId: String,
    val revision: String,
    val allowPatterns: List<String>,
    val expectedSha256: Map<String, String>,
    val purpose: String
)

object HuggingFacePolicy {
    private val repoId = Regex("[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
    private val commit = Regex("[0-9a-f]{40}")
    private val sha256 = Regex("[0-9a-f]{64}")

    fun validate(asset: HuggingFaceAsset) {
        require(repoId.matches(asset.repoId)) { "invalid Hugging Face repository id" }
        require(commit.matches(asset.revision)) { "revision must be a pinned 40-character commit" }
        require(asset.allowPatterns.isNotEmpty()) { "allowPatterns must be explicit" }
        require(asset.allowPatterns.none { it.contains("..") || it.startsWith("/") }) {
            "allowPatterns may not escape the asset root"
        }
        require(asset.expectedSha256.isNotEmpty()) { "expected file hashes are mandatory" }
        require(asset.expectedSha256.values.all(sha256::matches)) { "invalid expected SHA-256" }
        require(asset.purpose.isNotBlank()) { "asset purpose is mandatory" }
    }
}
