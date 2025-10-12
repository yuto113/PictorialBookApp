document.addEventListener('DOMContentLoaded', function () {
    var widget = document.getElementById('js-filter');
    var checkboxes = widget.querySelectorAll('.filter-cond input[type="checkbox"]');
    var items = widget.querySelectorAll('.filter-items li');
    
    var filter = function () {
        var checkedList = [];
        
        // チェックされたチェックボックスの値を取得
        checkboxes.forEach(function (checkbox) {
            if (checkbox.checked) {
                checkedList.push(checkbox.value);
            }
        });
        
        // 全ての項目を一旦非表示にする
        items.forEach(function (item) {
            item.style.display = 'none';
        });
        
        // チェックされたカテゴリーに該当する項目のみを表示する
        if (checkedList.length > 0) {
            checkedList.forEach(function (filterValue) {
                items.forEach(function (item) {
                    if (item.getAttribute('data-filter-key') === filterValue) {
                        item.style.display = 'block'; // または 'list-item'
                    }
                });
            });
        } else {
            // 何もチェックされていない場合は全ての項目を表示する
            items.forEach(function (item) {
                item.style.display = 'block'; // または 'list-item'
            });
        }
    };
    
    // チェックボックスの状態が変わったらfilter関数を呼び出す
    checkboxes.forEach(function (checkbox) {
        checkbox.addEventListener('change', filter);
    });
});