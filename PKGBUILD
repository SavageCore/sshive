# Maintainer: SavageCore
pkgname=sshive
pkgver=0.1.0
pkgrel=1
pkgdesc="Your hive of SSH connections - A modern SSH connection manager"
arch=('any')
url="https://github.com/SavageCore/sshive"
license=('MIT')
depends=('python-pyside6')
makedepends=('python-build' 'python-installer' 'python-hatchling')
source=("sshive-$pkgver.tar.gz::https://github.com/SavageCore/sshive/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 scripts/sshive.desktop "$pkgdir/usr/share/applications/sshive.desktop"
    install -Dm644 sshive/resources/icon.png "$pkgdir/usr/share/icons/hicolor/512x512/apps/sshive.png"
}
