from typing import Any

from pydantic import BaseModel


class IndustryIdentifier(BaseModel):
    type: str | None = None
    identifier: str | None = None


class Dimensions(BaseModel):
    height: str | None = None
    width: str | None = None
    thickness: str | None = None


class ImageLinks(BaseModel):
    smallThumbnail: str | None = None
    thumbnail: str | None = None
    small: str | None = None
    medium: str | None = None
    large: str | None = None
    extraLarge: str | None = None


class VolumeInfo(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] | None = None
    publisher: str | None = None
    publishedDate: str | None = None
    description: str | None = None
    industryIdentifiers: list[IndustryIdentifier] | None = None
    pageCount: int | None = None
    dimensions: Dimensions | None = None
    printType: str | None = None
    mainCategory: str | None = None
    categories: list[str] | None = None
    averageRating: float | None = None
    ratingsCount: int | None = None
    contentVersion: str | None = None
    imageLinks: ImageLinks | None = None
    language: str | None = None
    previewLink: str | None = None
    infoLink: str | None = None
    canonicalVolumeLink: str | None = None


class UserInfo(BaseModel):
    review: dict[str, Any] | None = None  # mylibrary.reviews Resource
    readingPosition: dict[str, Any] | None = (
        None  # mylibrary.readingpositions Resource
    )
    isPurchased: bool | None = None
    isPreordered: bool | None = None
    updated: str | None = None


class Price(BaseModel):
    amount: float | None = None
    currencyCode: str | None = None


class SaleInfo(BaseModel):
    country: str | None = None
    saleability: str | None = None
    onSaleDate: str | None = None
    isEbook: bool | None = None
    listPrice: Price | None = None
    retailPrice: Price | None = None
    buyLink: str | None = None


class FormatAccess(BaseModel):
    isAvailable: bool | None = None
    downloadLink: str | None = None
    acsTokenLink: str | None = None


class DownloadAccessRestriction(BaseModel):
    kind: str | None = None
    volumeId: str | None = None
    restricted: bool | None = None
    deviceAllowed: bool | None = None
    justAcquired: bool | None = None
    maxDownloadDevices: int | None = None
    downloadsAcquired: int | None = None
    nonce: str | None = None
    source: str | None = None
    reasonCode: str | None = None
    message: str | None = None
    signature: str | None = None


class AccessInfo(BaseModel):
    country: str | None = None
    viewability: str | None = None
    embeddable: bool | None = None
    publicDomain: bool | None = None
    textToSpeechPermission: str | None = None
    epub: FormatAccess | None = None
    pdf: FormatAccess | None = None
    webReaderLink: str | None = None
    accessViewStatus: str | None = None
    downloadAccess: DownloadAccessRestriction | None = None


class SearchInfo(BaseModel):
    textSnippet: str | None = None


class GoogleBookVolume(BaseModel):
    kind: str | None = None
    id: str | None = None
    etag: str | None = None
    selfLink: str | None = None
    volumeInfo: VolumeInfo | None = None
    userInfo: UserInfo | None = None
    saleInfo: SaleInfo | None = None
    accessInfo: AccessInfo | None = None
    searchInfo: SearchInfo | None = None


class GoogleBookVolumesList(BaseModel):
    kind: str | None = None
    items: list[GoogleBookVolume] | None = None
    totalItems: int | None = None
